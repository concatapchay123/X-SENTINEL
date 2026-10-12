from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from x_sentinel.api.schemas import CanonicalEvidenceResponse
from x_sentinel.audit.evidence import (
    CanonicalEvidence,
)
from x_sentinel.database.models import AnalysisJob
from x_sentinel.database.repositories.evidence import CanonicalEvidenceRepository


class EvidenceService:
    """Service layer orchestrating read-only access to immutable canonical evidence."""

    def __init__(self, repository: CanonicalEvidenceRepository | None = None):
        self._repository = repository

    def _repo(self, session: Session) -> CanonicalEvidenceRepository:
        return self._repository or CanonicalEvidenceRepository(session)

    def get_canonical_evidence(
        self,
        session: Session,
        identifier: str,
    ) -> CanonicalEvidence | None:
        """Retrieves and strictly validates integrity of canonical evidence for a job.

        Args:
            session: SQLAlchemy database session.
            identifier: Either the AnalysisJob UUID or the request_id.

        Returns:
            CanonicalEvidence object with verified SHA-256 digest, or None if job/evidence absent.

        Raises:
            EvidenceIntegrityError: If stored evidence fails SHA-256 integrity verification.
        """
        # Resolve job by UUID or request_id
        job: AnalysisJob | None = None
        try:
            parsed_uuid = uuid.UUID(str(identifier))
            job = session.get(AnalysisJob, parsed_uuid)
        except (ValueError, TypeError):
            pass

        if job is None:
            job = session.scalar(
                select(AnalysisJob).where(AnalysisJob.request_id == str(identifier))
            )

        if job is None:
            return None

        repo = self._repo(session)
        evidence = repo.get_canonical_evidence(job.request_id)
        if evidence is None:
            return None

        # verify_integrity raises EvidenceIntegrityError if hash does not match
        evidence.verify_integrity()
        return evidence

    @staticmethod
    def to_response(evidence: CanonicalEvidence) -> CanonicalEvidenceResponse:
        """Converts verified CanonicalEvidence into typed API response model."""
        return CanonicalEvidenceResponse(
            request_id=evidence.request_id,
            run_id=evidence.run_id,
            timestamp=evidence.timestamp,
            code_commit=evidence.code_commit,
            build_digest=evidence.build_digest,
            input_id=evidence.input_id,
            input_mode=evidence.input_mode,
            view_map_hash=evidence.view_map_hash,
            model_hash=evidence.model_hash,
            model_config_hash=evidence.model_config_hash,
            detector_config_hash=evidence.detector_config_hash,
            seed=evidence.seed,
            malware_score=evidence.malware_score,
            signals=evidence.signals,
            fusion_score=evidence.fusion_score,
            threshold_id=evidence.threshold_id,
            decision=evidence.decision,
            latency_ms=evidence.latency_ms,
            demo_mode=evidence.demo_mode,
            evidence_hash=evidence.evidence_hash or evidence.compute_hash(),
            verified=True,
        )
