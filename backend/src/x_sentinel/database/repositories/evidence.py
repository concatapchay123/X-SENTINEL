from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from x_sentinel.audit.evidence import (
    CanonicalEvidence,
    EvidenceIntegrityError,
    compute_evidence_hash,
)
from x_sentinel.audit.writer import AuditWriteFailureError
from x_sentinel.database.models import (
    AnalysisJob,
    AnalysisResultRecord,
    Artifact,
    AuditEvent,
    DetectorScore,
)


class CanonicalEvidenceRepository:
    """Repository for transactional persistence and retrieval of canonical detector evidence."""

    def __init__(self, session: Session):
        self.session = session

    def persist(
        self,
        evidence: CanonicalEvidence,
        user_id: uuid.UUID | None = None,
        model_version_id: uuid.UUID | None = None,
        evidence_uri: str | None = None,
        auto_commit: bool = True,
    ) -> tuple[AnalysisJob, AnalysisResultRecord, list[DetectorScore], Artifact, AuditEvent]:
        """Persists the full canonical evidence structure as an atomic transaction.

        If any error occurs during write or commit, an explicit rollback is performed,
        and AuditWriteFailureError is raised.
        """
        # Ensure evidence hash is computed
        evidence_with_hash = evidence.with_hash() if evidence.evidence_hash is None else evidence
        evidence_hash = evidence_with_hash.evidence_hash
        assert evidence_hash is not None

        # Check for duplicate request_id (prevent unauthorized overwrite)
        existing = self.session.scalar(
            select(AnalysisJob).where(AnalysisJob.request_id == evidence.request_id)
        )
        if existing is not None:
            raise AuditWriteFailureError(
                f"Duplicate request_id '{evidence.request_id}' already exists. Overwrite rejected."
            )

        try:
            job_id = uuid.uuid4()
            job_status = "quarantined" if evidence.decision == "QUARANTINE" else "completed"

            # Parse ISO timestamp safely
            try:
                created_dt = datetime.fromisoformat(evidence.timestamp.replace("Z", "+00:00"))
            except Exception:
                created_dt = datetime.now(timezone.utc)

            # 1. AnalysisJob
            job = AnalysisJob(
                id=job_id,
                request_id=evidence.request_id,
                user_id=user_id,
                model_version_id=model_version_id,
                status=job_status,
                input_mode=evidence.input_mode,
                input_sha256=evidence.input_id,
                config_version=evidence.detector_config_hash,
                demo_mode=evidence.demo_mode,
                created_at=created_dt,
                started_at=created_dt,
                completed_at=created_dt,
            )
            self.session.add(job)

            # Map decision to database allowed check constraint: ('unknown','pass','alert','quarantine')
            db_decision_map = {
                "PASS": "pass",
                "ALERT": "alert",
                "QUARANTINE": "quarantine",
                "DEMO_ONLY": "unknown",
            }
            db_decision = db_decision_map.get(evidence.decision, "unknown")

            # 2. AnalysisResultRecord
            result_record = AnalysisResultRecord(
                analysis_job_id=job_id,
                malware_score=evidence.malware_score,
                suspicion_score=evidence.fusion_score,
                threshold=None,
                decision=db_decision,
                latency_ms=evidence.latency_ms.get("end_to_end"),
                view_contributions={},
                result_json=evidence_with_hash.to_dict(),
                evidence_uri=evidence_uri or f"evidence://{evidence.request_id}",
                created_at=created_dt,
            )
            self.session.add(result_record)

            # 3. DetectorScore (M1..M5)
            scores: list[DetectorScore] = []
            for code in ("M1", "M2", "M3", "M4", "M5"):
                sig_val = evidence.signals.get(code.lower(), 0.0)
                score_rec = DetectorScore(
                    analysis_job_id=job_id,
                    detector_code=code,
                    score=sig_val,
                    diagnostics={"canonical": True},
                    created_at=created_dt,
                )
                self.session.add(score_rec)
                scores.append(score_rec)

            # 4. Artifact for canonical evidence
            uri = evidence_uri or f"evidence://{evidence.request_id}"
            artifact = Artifact(
                id=uuid.uuid4(),
                analysis_job_id=job_id,
                kind="evidence",
                uri=uri,
                sha256=evidence_hash,
                content_type="application/json",
                size_bytes=len(evidence_with_hash.to_canonical_json().encode("utf-8")),
                metadata_json={
                    "run_id": evidence.run_id,
                    "threshold_id": evidence.threshold_id,
                    "code_commit": evidence.code_commit,
                },
                created_at=created_dt,
            )
            self.session.add(artifact)

            # 5. Append-only AuditEvent
            audit_event = AuditEvent(
                request_id=evidence.request_id,
                user_id=user_id,
                event_type="evidence.persisted",
                entity_type="analysis_job",
                entity_id=str(job_id),
                payload={
                    "evidence_hash": evidence_hash,
                    "decision": evidence.decision,
                    "demo_mode": evidence.demo_mode,
                    "run_id": evidence.run_id,
                },
                created_at=created_dt,
            )
            self.session.add(audit_event)

            self.session.flush()

            if auto_commit:
                self.session.commit()

            return job, result_record, scores, artifact, audit_event

        except Exception as exc:
            self.session.rollback()
            raise AuditWriteFailureError(
                f"Database write failure while persisting evidence for {evidence.request_id}: {exc}"
            ) from exc

    def get_canonical_evidence(self, request_id: str) -> CanonicalEvidence | None:
        """Retrieves and verifies the canonical evidence stored for a request_id."""
        job = self.session.scalar(
            select(AnalysisJob).where(AnalysisJob.request_id == request_id)
        )
        if job is None:
            return None

        result_rec = self.session.get(AnalysisResultRecord, job.id)
        if result_rec is None or not result_rec.result_json:
            return None

        evidence = CanonicalEvidence.from_dict(result_rec.result_json)
        # Verify read-back integrity
        evidence.verify_integrity()
        return evidence
