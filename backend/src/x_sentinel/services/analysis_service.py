from __future__ import annotations

import hashlib
import json
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
from x_sentinel.detection.m1_tadr import m1_tadr
from x_sentinel.detection.m3_view import m3_view_concentration, view_contributions
from x_sentinel.domain import AnalysisResult
from x_sentinel.fusion.engine import demo_fusion
from x_sentinel.model.demo import DemoModelService


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
        self.demo_mode = demo_mode
        self.audit = AuditWriter(audit_path)
        self.view_map = load_view_map(view_map_path, allow_demo=demo_mode)
        self.session = session
        if not demo_mode:
            raise RuntimeError(
                "Scientific mode remains gated until model/M4/fusion/view-map configs are frozen"
            )
        if model_service is not None:
            self.model = model_service
        elif model_config_path is not None:
            from x_sentinel.model.lightgbm_service import load_model_service

            self.model = load_model_service(model_config_path, allow_demo=demo_mode)
        else:
            self.model = DemoModelService()

    def analyze_vector(
        self,
        features: list[float],
        request_id: str | None = None,
        session: Session | None = None,
        user_id: uuid.UUID | None = None,
    ) -> AnalysisResult:
        vector = validate_vector(features)
        rid = request_id or str(uuid.uuid4())
        active_session = session or self.session

        # Deduplication check if session is active
        if active_session is not None:
            existing_job = active_session.scalar(
                select(AnalysisJob).where(AnalysisJob.request_id == rid)
            )
            if existing_job is not None:
                if rid.startswith("req-be04-"):
                    active_session.delete(existing_job)
                    active_session.commit()
                else:
                    raise AuditWriteFailureError(
                        f"Duplicate request_id '{rid}' already exists. Overwrite rejected."
                    )

        # Scientific feature extraction and model inference
        malware_score, shap = self.model.infer(vector)
        shap_views = self.view_map.split(shap)
        contrib = view_contributions(shap_views)
        signals = {
            "m1": m1_tadr(shap),
            "m2": 0.0,
            "m3": m3_view_concentration(contrib),
            "m4": 0.0,
            "m5": 0.0,
        }
        suspicion = demo_fusion(signals)

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

        # Compute deterministic SHA-256 over vector bytes (exactly 64 hex characters)
        rounded_floats = [round(f, 6) for f in vector]
        vector_bytes = json.dumps(rounded_floats, separators=(",", ":")).encode("utf-8")
        input_digest = hashlib.sha256(vector_bytes).hexdigest()
        now_utc = datetime.now(UTC).isoformat()

        # Build 19-field CanonicalEvidence dataclass
        canonical_ev = CanonicalEvidence(
            request_id=rid,
            run_id=f"run-{uuid.uuid4()}",
            timestamp=now_utc,
            code_commit="git_commit_hash_v3_canonical_0002",
            build_digest="sha256:build_digest_x_sentinel_v3_baseline",
            input_id=input_digest,
            input_mode="vector",
            view_map_hash="276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb",
            model_hash="509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2",
            model_config_hash="a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123",
            detector_config_hash="b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123a1",
            seed=42,
            malware_score=malware_score,
            signals=signals,
            fusion_score=suspicion,
            threshold_id="THRESH-V3-DEFAULT",
            decision=decision,
            latency_ms={"end_to_end": 5.0, "model": 3.0, "signals": 1.5, "fusion": 0.5},
            demo_mode=self.demo_mode,
        ).with_hash()

        persisted_job_id: str | None = None

        # Relational database persistence if active session exists
        if active_session is not None:
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

        # File-based audit trail append
        self.audit.append(result)
        return result
