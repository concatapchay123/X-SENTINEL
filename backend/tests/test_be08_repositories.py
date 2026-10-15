from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from x_sentinel.audit.evidence import CanonicalEvidence
from x_sentinel.audit.writer import AuditWriteFailureError
from x_sentinel.config import settings
from x_sentinel.database.base import Base
from x_sentinel.database.models import (
    AnalysisJob,
    AnalysisResultRecord,
    Artifact,
    AuditEvent,
    DetectorScore,
)
from x_sentinel.database.repositories import (
    AnalysisJobRepository,
    AnalysisResultRepository,
    ArtifactRepository,
    AuditEventRepository,
    CanonicalEvidenceRepository,
    DetectorScoreRepository,
)


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
    """Creates a clean in-memory SQLite database and session for hermetic unit testing."""
    engine = create_engine("sqlite:///:memory:")
    # Normalize T-SQL N'...' server_defaults and SQLite BigInteger autoincrement
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


def _sample_evidence(request_id: str = "REQ-REPO-001") -> CanonicalEvidence:
    return CanonicalEvidence(
        request_id=request_id,
        run_id="RUN-REPO-001",
        timestamp="2026-10-12T15:00:00+00:00",
        code_commit="abcdef0123456789abcdef0123456789abcdef01",
        build_digest="sha256:build_digest_sample",
        input_id="sha256:input_digest_sample",
        input_mode="vector",
        view_map_hash="1" * 64,
        model_hash="2" * 64,
        model_config_hash="3" * 64,
        detector_config_hash="4" * 64,
        seed=42,
        malware_score=0.75,
        signals={"m1": 0.1, "m2": 0.2, "m3": 0.3, "m4": 0.4, "m5": 0.5},
        fusion_score=0.65,
        threshold_id="THRESH-01",
        decision="ALERT",
        latency_ms={"end_to_end": 6.8},
        demo_mode=False,
    ).with_hash()


class TestDatabaseRepositories:
    """Unit tests for repository implementations in x_sentinel.database.repositories."""

    def test_analysis_job_repository(self, db_session: Session) -> None:
        repo = AnalysisJobRepository(db_session)
        job_id = uuid.uuid4()
        job = AnalysisJob(
            id=job_id,
            request_id="REQ-TEST-JOB-01",
            status="queued",
            input_mode="vector",
            demo_mode=False,
        )
        persisted = repo.add(job)
        db_session.commit()

        assert persisted.id == job_id
        fetched = repo.get_by_id(job_id)
        assert fetched is not None
        assert fetched.request_id == "REQ-TEST-JOB-01"

        by_req = repo.get_by_request_id("REQ-TEST-JOB-01")
        assert by_req is not None
        assert by_req.id == job_id

        # Update status
        updated = repo.update_status(job_id, "completed")
        db_session.commit()
        assert updated.status == "completed"
        assert updated.completed_at is not None

        # List jobs
        jobs = repo.list_jobs(limit=10)
        assert len(jobs) == 1

    def test_analysis_result_repository(self, db_session: Session) -> None:
        job_repo = AnalysisJobRepository(db_session)
        res_repo = AnalysisResultRepository(db_session)

        job_id = uuid.uuid4()
        job = AnalysisJob(
            id=job_id,
            request_id="REQ-TEST-RES-01",
            status="completed",
            input_mode="vector",
            demo_mode=False,
        )
        job_repo.add(job)

        res = AnalysisResultRecord(
            analysis_job_id=job_id,
            malware_score=0.85,
            suspicion_score=0.90,
            threshold=0.50,
            decision="alert",
            latency_ms=9.2,
            result_json={"decision": "ALERT"},
        )
        res_repo.add(res)
        db_session.commit()

        fetched = res_repo.get_by_job_id(job_id)
        assert fetched is not None
        assert fetched.malware_score == 0.85
        assert fetched.decision == "alert"

    def test_detector_score_repository(self, db_session: Session) -> None:
        job_repo = AnalysisJobRepository(db_session)
        score_repo = DetectorScoreRepository(db_session)

        job_id = uuid.uuid4()
        job = AnalysisJob(
            id=job_id,
            request_id="REQ-TEST-SCORE-01",
            status="completed",
            input_mode="vector",
            demo_mode=False,
        )
        job_repo.add(job)

        scores = [
            DetectorScore(analysis_job_id=job_id, detector_code="M1", score=0.25),
            DetectorScore(analysis_job_id=job_id, detector_code="M2", score=0.35),
            DetectorScore(analysis_job_id=job_id, detector_code="M3", score=0.45),
            DetectorScore(analysis_job_id=job_id, detector_code="M4", score=0.55),
            DetectorScore(analysis_job_id=job_id, detector_code="M5", score=0.65),
        ]
        score_repo.add_many(scores)
        db_session.commit()

        all_scores = score_repo.get_by_job_id(job_id)
        assert len(all_scores) == 5
        m3_score = score_repo.get_by_job_and_detector(job_id, "M3")
        assert m3_score is not None
        assert m3_score.score == 0.45

    def test_artifact_repository(self, db_session: Session) -> None:
        repo = ArtifactRepository(db_session)
        art_id = uuid.uuid4()
        art = Artifact(
            id=art_id,
            kind="evidence",
            uri="artifacts/evidence/req01.json",
            sha256="5" * 64,
            size_bytes=2048,
        )
        repo.add(art)
        db_session.commit()

        fetched = repo.get_by_id(art_id)
        assert fetched is not None
        assert fetched.sha256 == "5" * 64

        by_hash = repo.get_by_sha256("5" * 64)
        assert len(by_hash) == 1
        assert by_hash[0].id == art_id

    def test_audit_event_repository_append_only(self, db_session: Session) -> None:
        repo = AuditEventRepository(db_session)
        ev = AuditEvent(
            request_id="REQ-AUDIT-01",
            event_type="analysis.created",
            entity_type="analysis_job",
            entity_id="JOB-01",
            payload={"status": "queued"},
        )
        persisted = repo.add(ev)
        db_session.commit()

        assert persisted.id is not None
        by_req = repo.get_by_request_id("REQ-AUDIT-01")
        assert len(by_req) == 1
        assert by_req[0].event_type == "analysis.created"

        # Contract verification: repository has NO delete or update methods
        assert not hasattr(repo, "delete")
        assert not hasattr(repo, "update")

    def test_canonical_evidence_repository_persistence_and_read_back(
        self, db_session: Session
    ) -> None:
        ev = _sample_evidence("REQ-PERSIST-01")
        repo = CanonicalEvidenceRepository(db_session)

        job, res, scores, art, audit_ev = repo.persist(ev, auto_commit=True)

        assert job.request_id == "REQ-PERSIST-01"
        assert res.decision == "alert"
        assert len(scores) == 5
        assert art.kind == "evidence"
        assert art.sha256 == ev.evidence_hash
        assert audit_ev.event_type == "evidence.persisted"

        # Read-back and integrity verification
        read_back_ev = repo.get_canonical_evidence("REQ-PERSIST-01")
        assert read_back_ev is not None
        assert read_back_ev.request_id == ev.request_id
        assert read_back_ev.evidence_hash == ev.evidence_hash
        assert read_back_ev.compute_hash() == ev.compute_hash()
        assert read_back_ev.verify_integrity() is True

    def test_canonical_evidence_repository_rejects_duplicate(
        self, db_session: Session
    ) -> None:
        ev = _sample_evidence("REQ-DUP-01")
        repo = CanonicalEvidenceRepository(db_session)
        repo.persist(ev, auto_commit=True)

        # Attempting to persist duplicate request_id must fail closed
        with pytest.raises(AuditWriteFailureError, match="Duplicate request_id.*already exists"):
            repo.persist(ev, auto_commit=True)

    @pytest.mark.skipif(not db_available, reason="live Microsoft SQL Server not reachable")
    def test_live_mssql_canonical_evidence_persistence_and_rollback(self) -> None:
        """Integration test on live canonical Microsoft SQL Server."""
        engine = create_engine(settings.database_url)
        unique_req = f"REQ-LIVE-MSSQL-{uuid.uuid4()}"
        ev = _sample_evidence(unique_req)

        with Session(engine) as session:
            repo = CanonicalEvidenceRepository(session)
            job, res, scores, art, audit_ev = repo.persist(ev, auto_commit=True)

            assert job.request_id == unique_req
            assert res.decision == "alert"

            # Read-back from real SQL Server
            read_back = repo.get_canonical_evidence(unique_req)
            assert read_back is not None
            assert read_back.request_id == unique_req
            assert read_back.verify_integrity() is True

            # Cleanup test record
            session.delete(job)
            session.commit()
