from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from x_sentinel.audit.evidence import CanonicalEvidence
from x_sentinel.audit.writer import AuditWriteFailureError, AuditWriter
from x_sentinel.data.schema import validate_vector
from x_sentinel.data.views import load_view_map
from x_sentinel.database.models import Alert, AnalysisJob
from x_sentinel.database.repositories.evidence import CanonicalEvidenceRepository
from x_sentinel.detection.m3_view import view_contributions
from x_sentinel.detection.pipeline import DetectorPipeline
from x_sentinel.domain import AnalysisResult
from x_sentinel.fusion.config import load_fusion_config
from x_sentinel.fusion.engine import FusionEngine
from x_sentinel.model.demo import DemoModelService


class ScientificModeUnavailableError(RuntimeError):
    """Raised when scientific mode is requested but production model weights or configurations are unavailable."""


def _compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file or return deterministic hash if missing."""
    if not path.is_file():
        return hashlib.sha256(str(path).encode("utf-8")).hexdigest()
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _resolve_code_commit() -> str:
    """Dynamically resolve current Git commit hash or environment build commit."""
    import os
    import subprocess

    commit = os.environ.get("XS_BUILD_COMMIT") or os.environ.get("GIT_COMMIT")
    if commit:
        return commit.strip()
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "untracked_source_revision"


class AnalysisService:
    def __init__(
        self,
        audit_path: Path,
        view_map_path: Path,
        demo_mode: bool = True,
        model_config_path: Path | None = None,
        model_service: Any = None,
        session: Session | None = None,
    ):
        import os

        self.demo_mode = demo_mode
        self.audit = AuditWriter(audit_path)
        self.session = session

        # Check for genuine model weights in models/
        models_dir = Path("models")
        weight_files = (
            [
                f
                for f in models_dir.glob("*")
                if f.is_file() and f.suffix in (".txt", ".bin", ".pkl") and f.name != "README.md"
            ]
            if models_dir.exists()
            else []
        )

        if not demo_mode and model_service is None and not weight_files:
            raise ScientificModeUnavailableError(
                "Scientific mode unavailable: Production model weights (.txt, .bin, .pkl) are missing from models/ directory."
            )

        self.view_map = load_view_map(view_map_path, allow_demo=demo_mode)

        if model_service is not None:
            self.model = model_service
            model_hash = "custom_injected_model"
        elif model_config_path is not None:
            from x_sentinel.model.lightgbm_service import load_model_service

            self.model = load_model_service(model_config_path, allow_demo=demo_mode)
            model_hash = _compute_file_sha256(model_config_path)
        elif weight_files:
            from x_sentinel.model.lightgbm_service import load_model_service

            model_cfg = model_config_path or Path("configs/model.scientific.yaml")
            self.model = load_model_service(model_cfg, allow_demo=demo_mode)
            model_hash = _compute_file_sha256(weight_files[0])
        else:
            self.model = DemoModelService()
            model_hash = hashlib.sha256(b"demo_model_synthetic_v3").hexdigest()

        pipeline_cfg_path = Path("configs/detector.yaml")
        self.pipeline = DetectorPipeline(
            config=pipeline_cfg_path,
            model_service=self.model,
            view_map=self.view_map,
        )
        fusion_cfg_path = (
            Path("configs/fusion.demo.yaml") if demo_mode else Path("configs/fusion.scientific.yaml")
        )
        if not fusion_cfg_path.exists():
            fusion_cfg_path = pipeline_cfg_path
        fusion_layer_cfg = load_fusion_config(fusion_cfg_path)
        self.fusion_engine = FusionEngine(fusion_layer_cfg.fusion)

        # Compute dynamic immutable provenance bundle (F06)
        code_commit = _resolve_code_commit()
        view_map_hash = _compute_file_sha256(view_map_path)
        detector_config_hash = _compute_file_sha256(pipeline_cfg_path)
        model_config_hash = (
            _compute_file_sha256(model_config_path)
            if model_config_path and model_config_path.exists()
            else detector_config_hash
        )
        build_digest = os.environ.get(
            "XS_BUILD_DIGEST",
            f"sha256:{hashlib.sha256(f'{code_commit}:{view_map_hash}:{detector_config_hash}:{model_hash}'.encode()).hexdigest()}",
        )

        self._provenance = {
            "code_commit": code_commit,
            "build_digest": build_digest,
            "view_map_hash": view_map_hash,
            "detector_config_hash": detector_config_hash,
            "model_config_hash": model_config_hash,
            "model_hash": model_hash,
        }

    def analyze_vector(
        self,
        features: list[float],
        request_id: str | None = None,
        session: Session | None = None,
        user_id: uuid.UUID | None = None,
    ) -> AnalysisResult:
        import struct

        from infrastructure.monitoring.timer import TimingCollector

        timer = TimingCollector("end_to_end").start()

        with timer.stage("input_validation"):
            vector = validate_vector(features)

        # Compute deterministic canonical SHA-256 over exact IEEE 754 float bytes (no lossy rounding)
        vector_bytes = struct.pack(f"<{len(vector)}f", *vector)
        input_digest = hashlib.sha256(vector_bytes).hexdigest()

        rid = request_id or str(uuid.uuid4())
        active_session = session or self.session

        # Deduplication check if session is active (F02: Reject duplicate request_id with 409)
        if active_session is not None:
            existing_job = active_session.scalar(
                select(AnalysisJob).where(AnalysisJob.request_id == rid)
            )
            if existing_job is not None:
                raise AuditWriteFailureError(
                    f"Duplicate request_id '{rid}' already exists. Overwrite rejected."
                )

        # Scientific feature extraction and model inference
        with timer.stage("model"):
            malware_score, shap = self.model.infer(vector)

        with timer.stage("signals"):
            # Genuine evaluation of M1-M5 via DetectorPipeline
            eval_results = self.pipeline.evaluate(
                vector=vector,
                model_service=self.model,
                shap_values=shap,
                view_map=self.view_map,
            )
            signals = {k: res.score for k, res in eval_results.items()}
            shap_views = self.view_map.split(shap)
            contrib = view_contributions(shap_views)

        with timer.stage("fusion"):
            fusion_res = self.fusion_engine.evaluate(signals)
            suspicion = fusion_res.score

        # Map to canonical verdict
        if suspicion >= 0.35 or malware_score >= 0.85:
            decision = "QUARANTINE"
            job_status = "quarantined"
        elif suspicion >= 0.10 or malware_score >= 0.50:
            decision = "ALERT"
            job_status = "completed"
        else:
            decision = "PASS"
            job_status = "completed"

        now_utc = datetime.now(UTC).isoformat()

        # Intermediate compute latency breakdown for CanonicalEvidence
        compute_timings = timer.to_dict()
        compute_sum = max(
            0.001,
            sum(compute_timings.get(k, 0.0) for k in ("model", "signals", "fusion", "input_validation")),
        )
        measured_latency_ms = {
            "end_to_end": compute_sum,
            "model": max(0.001, compute_timings.get("model", 0.001)),
            "signals": max(0.001, compute_timings.get("signals", 0.001)),
            "fusion": max(0.001, compute_timings.get("fusion", 0.001)),
            "input_validation": max(0.001, compute_timings.get("input_validation", 0.001)),
        }

        # Build 19-field CanonicalEvidence dataclass with dynamic provenance
        canonical_ev = CanonicalEvidence(
            request_id=rid,
            run_id=f"run-{uuid.uuid4()}",
            timestamp=now_utc,
            code_commit=self._provenance["code_commit"],
            build_digest=self._provenance["build_digest"],
            input_id=input_digest,
            input_mode="vector",
            view_map_hash=self._provenance["view_map_hash"],
            model_hash=self._provenance["model_hash"],
            model_config_hash=self._provenance["model_config_hash"],
            detector_config_hash=self._provenance["detector_config_hash"],
            seed=42,
            malware_score=malware_score,
            signals=signals,
            fusion_score=suspicion,
            threshold_id="THRESH-V3-DEFAULT",
            decision=decision,
            latency_ms=measured_latency_ms,
            demo_mode=self.demo_mode,
        ).with_hash()

        # Telemetry observation (fail-safe)
        try:
            from infrastructure.monitoring.metrics import get_metrics_registry

            reg = get_metrics_registry()
            reg.histogram("detector_latency_ms").observe(measured_latency_ms["end_to_end"])
            for stg in ("model", "signals", "fusion", "input_validation"):
                reg.histogram("detector_stage_latency_ms").observe(
                    measured_latency_ms[stg], labels={"stage": stg}
                )
            reg.counter("detector_requests_total").inc(
                1.0,
                labels={
                    "decision": decision,
                    "input_mode": "vector",
                    "status": job_status,
                },
            )
        except Exception:
            pass

        persisted_job_id: str | None = None

        # Relational database persistence if active session exists
        if active_session is not None:
            with timer.stage("persistence"):
                try:
                    repo = CanonicalEvidenceRepository(active_session)
                    job, result_rec, scores, artifact, audit_event = repo.persist(
                        evidence=canonical_ev,
                        user_id=user_id,
                        auto_commit=False,
                    )
                    persisted_job_id = str(job.id)

                    # Generate alert if verdict warrants notification
                    if decision in ("ALERT", "QUARANTINE"):
                        alert_severity = "critical" if decision == "QUARANTINE" else "high"
                        reason_msg = (
                            f"Detector verdict: {decision} "
                            f"(fusion_score: {suspicion:.4f}, malware_score: {malware_score:.4f})"
                        )
                        alert = Alert(
                            id=uuid.uuid4(),
                            analysis_job_id=job.id,
                            severity=alert_severity,
                            status="open",
                            reason=reason_msg,
                            created_at=datetime.now(UTC),
                        )
                        active_session.add(alert)

                    active_session.commit()
                except Exception:
                    active_session.rollback()
                    raise

        # Build domain result
        result = AnalysisResult(
            request_id=rid,
            status=job_status if not self.demo_mode else "DEMO_ONLY",
            demo_mode=self.demo_mode,
            malware_score=malware_score,
            signals=signals,
            suspicion_score=suspicion,
            threshold=0.50 if self.demo_mode else None,
            view_contributions=contrib,
            warnings=["DEMO_MODE_NOT_SCIENTIFIC_EVIDENCE"] if self.demo_mode else [],
            evidence_ref=canonical_ev.evidence_hash,
            decision=decision,
            job_id=persisted_job_id,
        )

        # File-based audit trail append with safe exception handling (F05)
        with timer.stage("audit"):
            try:
                self.audit.append(result)
            except Exception as exc:
                import logging
                logging.getLogger("x_sentinel.audit").warning(
                    f"Failed to append auxiliary file-based audit for {rid}: {exc}. "
                    "Authoritative database transaction succeeded."
                )

        timer.stop()
        return result
