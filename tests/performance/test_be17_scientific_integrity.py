from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from x_sentinel.audit.evidence import (
    CanonicalEvidence,
)
from x_sentinel.config import settings
from x_sentinel.database.models import Base
from x_sentinel.database.repositories.evidence import CanonicalEvidenceRepository
from x_sentinel.services.analysis_service import AnalysisService


@pytest.fixture
def test_db_session():
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
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class TestScientificAndSecurityIntegrity:
    def test_detector_scientific_truth_unaltered_by_timing_instrumentation(
        self, tmp_path: Path, test_db_session
    ) -> None:
        """Assert that model predictions, M1-M5 signals, fusion score, and decision

        are 100% deterministic and unaffected by high-resolution timing instrumentation.
        """
        audit_file = tmp_path / "test_audit.jsonl"
        view_map_file = settings.config_dir / "views.demo.yaml"

        service = AnalysisService(
            audit_path=audit_file,
            view_map_path=view_map_file,
            demo_mode=True,
            session=test_db_session,
        )

        test_features = [0.1] * 2381

        res1 = service.analyze_vector(test_features, request_id="req-integ-001")
        res2 = service.analyze_vector(test_features, request_id="req-integ-002")

        # Scientific scores must match exactly
        assert res1.malware_score == pytest.approx(res2.malware_score, abs=1e-9)
        assert res1.suspicion_score == pytest.approx(res2.suspicion_score, abs=1e-9)
        assert res1.decision == res2.decision
        assert res1.signals == res2.signals
        assert res1.view_contributions == res2.view_contributions

        # Fetch canonical evidence from DB repo and verify cryptographic integrity
        repo = CanonicalEvidenceRepository(test_db_session)
        ev1 = repo.get_canonical_evidence("req-integ-001")
        ev2 = repo.get_canonical_evidence("req-integ-002")

        assert ev1 is not None and ev2 is not None
        # Cryptographic integrity check: SHA-256 evidence hash matches canonical fields
        assert ev1.verify_integrity() is True
        assert ev2.verify_integrity() is True

        # Input ID must be deterministic hash over rounded vector bytes
        assert ev1.input_id == ev2.input_id

    def test_canonical_evidence_immutability_enforced(self) -> None:
        ev = CanonicalEvidence(
            request_id="req-frozen-001",
            run_id="run-frozen-001",
            timestamp="2026-10-13T10:00:00+00:00",
            code_commit="git_commit_hash_v3_canonical_0002",
            build_digest="sha256:build_digest_x_sentinel_v3_baseline",
            input_id="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            input_mode="vector",
            view_map_hash="276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb",
            model_hash="509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2",
            model_config_hash="a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123",
            detector_config_hash="b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123a1",
            seed=42,
            malware_score=0.25,
            signals={"m1": 0.1, "m2": 0.0, "m3": 0.05, "m4": 0.0, "m5": 0.0},
            fusion_score=0.15,
            threshold_id="THRESH-V3-DEFAULT",
            decision="PASS",
            latency_ms={"end_to_end": 5.2, "model": 3.1},
            demo_mode=False,
        ).with_hash()

        # Frozen dataclass rejects attribute mutations
        with pytest.raises((AttributeError, TypeError)):
            ev.decision = "QUARANTINE"  # type: ignore[misc]

    def test_timing_keys_non_negative_in_evidence(
        self, tmp_path: Path, test_db_session
    ) -> None:
        audit_file = tmp_path / "test_audit_lat.jsonl"
        view_map_file = settings.config_dir / "views.demo.yaml"

        service = AnalysisService(
            audit_path=audit_file,
            view_map_path=view_map_file,
            demo_mode=True,
            session=test_db_session,
        )

        _ = service.analyze_vector([0.05] * 2381, request_id="req-lat-check")
        repo = CanonicalEvidenceRepository(test_db_session)
        ev = repo.get_canonical_evidence("req-lat-check")

        assert ev is not None
        assert "end_to_end" in ev.latency_ms
        assert "model" in ev.latency_ms
        assert "signals" in ev.latency_ms
        assert "fusion" in ev.latency_ms
        assert "input_validation" in ev.latency_ms

        for _k, v in ev.latency_ms.items():
            assert isinstance(v, float)
            assert v >= 0.0
