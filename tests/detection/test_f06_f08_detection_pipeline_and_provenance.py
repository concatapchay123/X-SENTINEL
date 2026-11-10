"""Regression tests for Batch D: F06 (Dynamic Provenance) and F08 (M1-M5 Pipeline & Scientific Mode Guard)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from x_sentinel.database.models import (
    Alert,
    AnalysisJob,
    AnalysisResultRecord,
    Artifact,
    AuditEvent,
    Base,
    DetectorScore,
    User,
)
from x_sentinel.services.analysis_service import (
    AnalysisService,
    ScientificModeUnavailableError,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def in_memory_db():
    from sqlalchemy import Integer
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for col in Base.metadata.tables["audit_events"].columns:
        if col.name == "id":
            col.type = Integer()

    target_tables = [
        User.__table__,
        AnalysisJob.__table__,
        AnalysisResultRecord.__table__,
        DetectorScore.__table__,
        Artifact.__table__,
        Alert.__table__,
        AuditEvent.__table__,
    ]
    for table in target_tables:
        for col in table.columns:
            if col.server_default is not None and hasattr(col.server_default, "arg"):
                text_str = str(col.server_default.arg)
                if "N'" in text_str:
                    col.server_default.arg.text = text_str.replace("N'", "'")
        table.create(engine)

    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


def test_f06_dynamic_provenance_not_hardcoded(tmp_path: Path):
    """Verify that provenance hashes are dynamically calculated and reflect the actual environment."""
    audit_file = tmp_path / "audit.jsonl"
    view_path = PROJECT_ROOT / "configs" / "views.demo.yaml"

    service = AnalysisService(
        audit_path=audit_file,
        view_map_path=view_path,
        demo_mode=True,
    )

    # Provenance must not contain legacy static string
    assert service._provenance["code_commit"] != "git_commit_hash_v3_canonical_0002"
    assert len(service._provenance["code_commit"]) > 0

    assert service._provenance["build_digest"] != "sha256:build_digest_x_sentinel_v3_baseline"
    assert service._provenance["build_digest"].startswith("sha256:")

    # Hashes must be 64-character hex strings
    assert len(service._provenance["view_map_hash"]) == 64
    assert len(service._provenance["detector_config_hash"]) == 64


def test_f06_dynamic_provenance_in_canonical_evidence(tmp_path: Path, in_memory_db):
    """Verify that generated CanonicalEvidence uses the dynamic provenance bundle."""
    audit_file = tmp_path / "audit.jsonl"
    view_path = PROJECT_ROOT / "configs" / "views.demo.yaml"

    service = AnalysisService(
        audit_path=audit_file,
        view_map_path=view_path,
        demo_mode=True,
        session=in_memory_db,
    )

    vector = [0.1] * 2381
    res = service.analyze_vector(features=vector, request_id="req-prov-test-01")
    assert res.decision in ("PASS", "ALERT", "QUARANTINE")

    # Read persisted records and verify dynamic provenance
    from sqlalchemy import select
    result_rec = in_memory_db.scalar(select(AnalysisResultRecord))
    assert result_rec is not None
    assert result_rec.result_json["code_commit"] != "git_commit_hash_v3_canonical_0002"
    assert result_rec.result_json["code_commit"] == service._provenance["code_commit"]

    artifact = in_memory_db.scalar(select(Artifact))
    assert artifact is not None
    assert artifact.metadata_json["code_commit"] == service._provenance["code_commit"]


def test_f08_demo_pipeline_evaluates_m1_m5(tmp_path: Path, in_memory_db):
    """Verify that Demo mode evaluates real M1-M5 signals via DetectorPipeline."""
    audit_file = tmp_path / "audit.jsonl"
    view_path = PROJECT_ROOT / "configs" / "views.demo.yaml"

    service = AnalysisService(
        audit_path=audit_file,
        view_map_path=view_path,
        demo_mode=True,
        session=in_memory_db,
    )

    vector = [0.25] * 2381
    res = service.analyze_vector(features=vector, request_id="req-m1m5-eval-01")

    # All 5 signals must be present in the result
    assert "m1" in res.signals
    assert "m2" in res.signals
    assert "m3" in res.signals
    assert "m4" in res.signals
    assert "m5" in res.signals

    # All signals must be valid floats between 0.0 and 1.0
    for sig_name, sig_score in res.signals.items():
        assert 0.0 <= sig_score <= 1.0, f"Signal {sig_name} score {sig_score} out of bounds"


def test_f08_scientific_mode_fails_closed_when_weights_missing(tmp_path: Path):
    """Verify that scientific mode raises ScientificModeUnavailableError when weights are missing."""
    audit_file = tmp_path / "audit.jsonl"
    view_path = PROJECT_ROOT / "configs" / "views.scientific.yaml"

    with pytest.raises(ScientificModeUnavailableError, match="Scientific mode unavailable"):
        AnalysisService(
            audit_path=audit_file,
            view_map_path=view_path,
            demo_mode=False,
        )


def test_f08_api_returns_503_for_scientific_mode_without_weights():
    """Verify that get_analysis_service raises HTTP 503 when demo_mode=False and weights missing."""
    from x_sentinel.api.routes import get_analysis_service
    from x_sentinel.config import settings

    orig_demo = settings.demo_mode
    try:
        settings.demo_mode = False
        with pytest.raises(HTTPException) as exc_info:
            get_analysis_service(db=None)  # type: ignore[arg-type]
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["code"] == "XS_SCIENTIFIC_UNAVAILABLE"
    finally:
        settings.demo_mode = orig_demo
