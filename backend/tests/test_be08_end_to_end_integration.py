from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from x_sentinel.audit.evidence import CanonicalEvidence
from x_sentinel.audit.manager import AuditEvidenceManager
from x_sentinel.audit.writer import AuditWriter
from x_sentinel.config import settings
from x_sentinel.data.views import load_view_map
from x_sentinel.database.base import Base
from x_sentinel.database.repositories.evidence import CanonicalEvidenceRepository
from x_sentinel.detection.pipeline import DetectorPipeline
from x_sentinel.fusion import (
    CalibrationEngine,
    DecisionPolicy,
    FusionEngine,
    load_fusion_config,
)
from x_sentinel.model.demo import DemoModelService


from x_sentinel.database.models import AnalysisJob


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


class TestEndToEndEvidenceLifecycle:
    """Verifies end-to-end evidence lifecycle from detector output to persistent verification."""

    def test_full_pipeline_to_canonical_evidence_and_database(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        # Step 1: Initialize detector components (BE-04, BE-05, BE-06, BE-07)
        view_map = load_view_map(Path("configs/views.demo.yaml"), allow_demo=True)
        model_service = DemoModelService()
        pipeline = DetectorPipeline(view_map=view_map, model_service=model_service)

        fusion_cfg = load_fusion_config("configs/detector.yaml")
        fusion_engine = FusionEngine(fusion_cfg.fusion)
        calib_engine = CalibrationEngine(fusion_cfg.calibration, demo_mode=True)
        threshold = calib_engine.resolve()
        policy = DecisionPolicy(
            alert_threshold=threshold,
            quarantine_threshold=calib_engine.quarantine_threshold,
            demo_mode=True,
        )

        # Step 2: Run inference on vector
        vector = [0.0] * 2381
        vector[0] = 50.0
        vector[1] = 25.0
        malware_score, _ = model_service.infer(vector)
        signals = pipeline.scores(vector, model_service=model_service, view_map=view_map)
        fusion_result = fusion_engine.evaluate(signals)
        decision_result = policy.evaluate(fusion_result.score)

        req_id = f"REQ-E2E-{uuid.uuid4()}"
        run_id = f"RUN-E2E-{uuid.uuid4()}"
        timestamp_str = datetime.now(timezone.utc).isoformat()

        # Step 3: Construct CanonicalEvidence
        canonical_evidence = CanonicalEvidence(
            request_id=req_id,
            run_id=run_id,
            timestamp=timestamp_str,
            code_commit="git_commit_hash_1234567890abcdef12345678",
            build_digest="sha256:build_digest_sample_1234567890abcdef",
            input_id="sha256:input_vector_digest_1234567890abcdef",
            input_mode="vector",
            view_map_hash="276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb",
            model_hash="509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2",
            model_config_hash="a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123",
            detector_config_hash="b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123a1",
            seed=42,
            malware_score=malware_score,
            signals=signals,
            fusion_score=fusion_result.score,
            threshold_id="THRESH-DEMO-01",
            decision=decision_result.candidate_verdict,
            latency_ms={"end_to_end": 6.5, "model": 2.1, "fusion": 0.4},
            demo_mode=True,
        ).with_hash()

        assert canonical_evidence.evidence_hash is not None
        assert canonical_evidence.verify_integrity() is True

        # Step 4: Durably persist via AuditEvidenceManager
        audit_file = tmp_path / "events.jsonl"
        manager = AuditEvidenceManager(audit_path=audit_file)
        evidence_hash, job_id = manager.record_evidence(
            canonical_evidence,
            session=db_session,
            write_file=True,
        )

        assert evidence_hash == canonical_evidence.evidence_hash
        assert job_id is not None
        assert audit_file.exists()

        # Step 5: Read-back from database and verify integrity
        repo = CanonicalEvidenceRepository(db_session)
        stored_ev = repo.get_canonical_evidence(req_id)
        assert stored_ev is not None
        assert stored_ev.evidence_hash == evidence_hash
        assert stored_ev.verify_integrity() is True
        assert stored_ev.malware_score == malware_score
        assert stored_ev.fusion_score == fusion_result.score
        assert stored_ev.signals == signals

    @pytest.mark.skipif(not db_available, reason="live Microsoft SQL Server not reachable")
    def test_live_mssql_full_pipeline_persistence(self, tmp_path: Path) -> None:
        """End-to-end integration test directly against live Microsoft SQL Server."""
        engine = create_engine(settings.database_url)
        req_id = f"REQ-LIVE-E2E-{uuid.uuid4()}"
        run_id = f"RUN-LIVE-E2E-{uuid.uuid4()}"
        timestamp_str = datetime.now(timezone.utc).isoformat()

        canonical_evidence = CanonicalEvidence(
            request_id=req_id,
            run_id=run_id,
            timestamp=timestamp_str,
            code_commit="git_commit_hash_1234567890abcdef12345678",
            build_digest="sha256:build_digest_sample_1234567890abcdef",
            input_id="sha256:input_vector_digest_1234567890abcdef",
            input_mode="vector",
            view_map_hash="276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb",
            model_hash="509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2",
            model_config_hash="a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123",
            detector_config_hash="b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123a1",
            seed=42,
            malware_score=0.77,
            signals={"m1": 0.1, "m2": 0.2, "m3": 0.3, "m4": 0.4, "m5": 0.5},
            fusion_score=0.66,
            threshold_id="THRESH-LIVE-01",
            decision="ALERT",
            latency_ms={"end_to_end": 7.0},
            demo_mode=False,
        ).with_hash()

        audit_file = tmp_path / "live_audit.jsonl"
        manager = AuditEvidenceManager(audit_path=audit_file)

        with Session(engine) as session:
            ev_hash, job_id = manager.record_evidence(
                canonical_evidence, session=session, require_scientific=True, write_file=True
            )
            assert ev_hash == canonical_evidence.evidence_hash
            assert job_id is not None

            # Read-back
            repo = CanonicalEvidenceRepository(session)
            stored = repo.get_canonical_evidence(req_id)
            assert stored is not None
            assert stored.verify_integrity() is True

            # Cleanup
            job = repo.session.get(AnalysisJob, job_id)
            if job:
                repo.session.delete(job)
                repo.session.commit()
