from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from x_sentinel.audit.evidence import CanonicalEvidence
from x_sentinel.audit.manager import AuditEvidenceManager
from x_sentinel.audit.writer import AuditWriteFailureError, AuditWriter
from x_sentinel.config import settings
from x_sentinel.database.base import Base
from x_sentinel.database.models import AnalysisJob
from x_sentinel.database.repositories.evidence import CanonicalEvidenceRepository


def _is_db_connected() -> bool:
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(Base.metadata.tables["analysis_jobs"].select().limit(1))
        engine.dispose()
        return True
    except Exception:
        return False


db_available = _is_db_connected()


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    for col in Base.metadata.tables["audit_events"].columns:
        if col.name == "id":
            from sqlalchemy import Integer
            col.type = Integer()
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if col.server_default is not None:
                text_str = str(col.server_default.arg)
                if "N'" in text_str:
                    col.server_default.arg.text = text_str.replace("N'", "'")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _sample_evidence(request_id: str = "REQ-FAIL-001") -> CanonicalEvidence:
    return CanonicalEvidence(
        request_id=request_id,
        run_id="RUN-FAIL-001",
        timestamp="2026-10-12T15:15:00+00:00",
        code_commit="abcdef0123456789abcdef0123456789abcdef01",
        build_digest="sha256:build_digest_fail",
        input_id="sha256:input_digest_fail",
        input_mode="vector",
        view_map_hash="1" * 64,
        model_hash="2" * 64,
        model_config_hash="3" * 64,
        detector_config_hash="4" * 64,
        seed=42,
        malware_score=0.95,
        signals={"m1": 0.5, "m2": 0.6, "m3": 0.7, "m4": 0.8, "m5": 0.9},
        fusion_score=0.88,
        threshold_id="THRESH-01",
        decision="QUARANTINE",
        latency_ms={"end_to_end": 7.5},
        demo_mode=False,
    ).with_hash()


class TestAuditWriteFailure:
    """Acceptance tests for audit and evidence write failure handling."""

    def test_database_commit_failure_raises_audit_write_failure_and_rolls_back(
        self, db_session: Session
    ) -> None:
        """Inject commit failure: must rollback, leave zero partial rows, and raise AuditWriteFailureError."""
        ev = _sample_evidence("REQ-COMMIT-FAIL-01")
        repo = CanonicalEvidenceRepository(db_session)

        # Mock session.commit to simulate database connection loss or disk failure
        original_commit = db_session.commit

        def failing_commit():
            raise OperationalError("Simulated DB connection lost", params={}, orig=Exception())

        db_session.commit = failing_commit  # type: ignore

        with pytest.raises(
            AuditWriteFailureError,
            match="Database write failure while persisting evidence",
        ):
            repo.persist(ev, auto_commit=True)

        # Restore commit to check database state
        db_session.commit = original_commit  # type: ignore

        # Verify that rollback executed: zero jobs or orphan records were persisted
        job = db_session.scalar(
            select(AnalysisJob).where(AnalysisJob.request_id == "REQ-COMMIT-FAIL-01")
        )
        assert job is None, "Rollback failed! Orphan record found in database."

    def test_file_audit_write_failure_raises_audit_write_failure(self, tmp_path: Path) -> None:
        """Writing to an unwriteable directory or path must raise AuditWriteFailureError."""
        unwriteable_path = tmp_path / "blocked_dir"
        unwriteable_path.mkdir()

        writer = AuditWriter(unwriteable_path)
        ev = _sample_evidence("REQ-FILE-FAIL-01")

        with pytest.raises(AuditWriteFailureError, match="Failed to append audit event"):
            writer.append_evidence(ev)

    def test_manager_fail_closed_on_db_persistence_error(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        """Manager must fail closed on database persistence failure without reporting false success."""
        log_file = tmp_path / "audit.jsonl"
        writer = AuditWriter(log_file)
        manager = AuditEvidenceManager(audit_writer=writer)
        ev = _sample_evidence("REQ-MGR-FAIL-01")

        def failing_commit():
            raise OperationalError("Simulated DB crash", params={}, orig=Exception())

        db_session.commit = failing_commit  # type: ignore

        with pytest.raises(AuditWriteFailureError):
            manager.record_evidence(ev, session=db_session)

        db_session.rollback()

    def test_detector_truth_uncontaminated_on_write_failure(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        """Detector mathematical values must remain identical before and after a write failure."""
        ev = _sample_evidence("REQ-TRUTH-PRESERVED-01")
        original_malware = ev.malware_score
        original_fusion = ev.fusion_score
        original_signals = dict(ev.signals)
        original_decision = ev.decision

        log_file = tmp_path / "audit.jsonl"
        writer = AuditWriter(log_file)
        manager = AuditEvidenceManager(audit_writer=writer)

        db_session.commit = MagicMock(side_effect=OperationalError("Disk full", params={}, orig=Exception()))

        with pytest.raises(AuditWriteFailureError):
            manager.record_evidence(ev, session=db_session)

        assert ev.malware_score == original_malware
        assert ev.fusion_score == original_fusion
        assert ev.signals == original_signals
        assert ev.decision == original_decision

    def test_zero_jev_ai_involvement_during_failure_recovery(
        self, db_session: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verifies that no Jev AI or external network calls are made during persistence failures."""
        import httpx

        def forbidden_call(*args, **kwargs):
            raise AssertionError("External AI or network call forbidden during failure handling!")

        monkeypatch.setattr(httpx, "post", forbidden_call)
        monkeypatch.setattr(httpx, "get", forbidden_call)

        ev = _sample_evidence("REQ-NO-AI-FAIL-01")
        repo = CanonicalEvidenceRepository(db_session)
        db_session.commit = MagicMock(side_effect=OperationalError("Network drop", params={}, orig=Exception()))

        with pytest.raises(AuditWriteFailureError):
            repo.persist(ev, auto_commit=True)

    @pytest.mark.skipif(not db_available, reason="live Microsoft SQL Server not reachable")
    def test_live_mssql_rollback_on_injected_commit_error(self) -> None:
        """Verifies transaction rollback on real live Microsoft SQL Server."""
        engine = create_engine(settings.database_url)
        unique_req = f"REQ-LIVE-FAIL-{uuid.uuid4()}"
        ev = _sample_evidence(unique_req)

        with Session(engine) as session:
            repo = CanonicalEvidenceRepository(session)
            session.commit = MagicMock(side_effect=OperationalError("Simulated drop", params={}, orig=Exception()))

            with pytest.raises(AuditWriteFailureError):
                repo.persist(ev, auto_commit=True)

        with Session(engine) as session:
            job = session.scalar(select(AnalysisJob).where(AnalysisJob.request_id == unique_req))
            assert job is None, "Rollback failed on live SQL Server! Found orphan record."
