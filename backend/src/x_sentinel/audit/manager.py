from __future__ import annotations

from pathlib import Path
from typing import Any
import uuid

from sqlalchemy.orm import Session

from x_sentinel.audit.evidence import (
    CanonicalEvidence,
    EvidenceIntegrityError,
    ScientificEvidenceRejectedError,
)
from x_sentinel.audit.writer import AuditWriteFailureError, AuditWriter
from x_sentinel.database.models import (
    AnalysisJob,
    AnalysisResultRecord,
    Artifact,
    AuditEvent,
    DetectorScore,
)
from x_sentinel.database.repositories.evidence import CanonicalEvidenceRepository


class AuditEvidenceManager:
    """Coordinates persistence of immutable canonical evidence and artifacts.

    Enforces fail-closed semantics:
    - If database or audit file writes fail, an AuditWriteFailureError is raised.
    - Transaction rollback occurs automatically on failure.
    - Zero false persistence acknowledgement.
    - Zero mutation of detector truth.
    - Zero Jev AI interference with canonical scientific evidence.
    """

    def __init__(
        self,
        audit_writer: AuditWriter | None = None,
        audit_path: Path | str | None = None,
    ):
        if audit_writer is not None:
            self.writer = audit_writer
        elif audit_path is not None:
            self.writer = AuditWriter(audit_path)
        else:
            self.writer = None

    def record_evidence(
        self,
        evidence: CanonicalEvidence,
        session: Session | None = None,
        require_scientific: bool = False,
        evidence_uri: str | None = None,
        user_id: uuid.UUID | None = None,
        model_version_id: uuid.UUID | None = None,
        write_file: bool = True,
    ) -> tuple[str, uuid.UUID | None]:
        """Validates and durably records canonical evidence to DB and/or file.

        Args:
            evidence: The CanonicalEvidence instance.
            session: Optional SQLAlchemy Session for relational persistence.
            require_scientific: If True, rejects demo_mode=True.
            evidence_uri: Optional URI where the raw evidence artifact is stored.
            user_id: Optional user UUID.
            model_version_id: Optional model version UUID.
            write_file: Whether to append to JSONL audit file if writer is configured.

        Returns:
            tuple[str, uuid.UUID | None]: (evidence_hash, analysis_job_id)

        Raises:
            ScientificEvidenceRejectedError: If require_scientific=True and demo_mode=True.
            AuditWriteFailureError: If database or file persistence fails.
        """
        # Validate for scientific mode if required
        if require_scientific:
            evidence.validate_for_scientific_acceptance()

        # Ensure evidence hash is computed and verified
        evidence_with_hash = evidence.with_hash() if evidence.evidence_hash is None else evidence
        evidence_with_hash.verify_integrity()
        evidence_hash = evidence_with_hash.evidence_hash
        assert evidence_hash is not None

        job_id: uuid.UUID | None = None

        # Step 1: Database persistence if session is provided
        if session is not None:
            repo = CanonicalEvidenceRepository(session)
            try:
                job, result, scores, artifact, audit_event = repo.persist(
                    evidence=evidence_with_hash,
                    user_id=user_id,
                    model_version_id=model_version_id,
                    evidence_uri=evidence_uri,
                    auto_commit=True,
                )
                job_id = job.id
            except Exception as exc:
                # CanonicalEvidenceRepository already guarantees rollback and raises AuditWriteFailureError
                if isinstance(exc, AuditWriteFailureError):
                    raise
                raise AuditWriteFailureError(
                    f"Relational evidence persistence failed for request {evidence.request_id}: {exc}"
                ) from exc

        # Step 2: File-based audit trail persistence if requested
        if write_file and self.writer is not None:
            try:
                self.writer.append_evidence(evidence_with_hash)
            except Exception as exc:
                raise AuditWriteFailureError(
                    f"Audit file persistence failed for request {evidence.request_id}: {exc}"
                ) from exc

        return evidence_hash, job_id

    def verify_stored_evidence(
        self,
        request_id: str,
        session: Session,
    ) -> bool:
        """Verifies the integrity of evidence stored in the database."""
        repo = CanonicalEvidenceRepository(session)
        evidence = repo.get_canonical_evidence(request_id)
        if evidence is None:
            raise ValueError(f"Evidence for request '{request_id}' not found.")
        return evidence.verify_integrity()
