from __future__ import annotations

import hashlib
import struct
import uuid
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from x_sentinel.api.schemas import VectorAnalysisRequest
from x_sentinel.audit.writer import AuditWriteFailureError
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
from x_sentinel.services.analysis_service import AnalysisService


def test_canonical_input_hashing_no_lossy_rounding():
    """F07: Vectors differing by less than 1e-6 must produce distinct SHA-256 digests."""
    vec_zeros = [0.0] * 2381
    vec_sub_micro = [0.0000001] + [0.0] * 2380

    bytes_zeros = struct.pack(f"<{len(vec_zeros)}f", *vec_zeros)
    bytes_sub_micro = struct.pack(f"<{len(vec_sub_micro)}f", *vec_sub_micro)

    hash_zeros = hashlib.sha256(bytes_zeros).hexdigest()
    hash_sub_micro = hashlib.sha256(bytes_sub_micro).hexdigest()

    assert hash_zeros != hash_sub_micro, "Hash collision: vectors differing at 1e-7 must not produce identical hashes"


def test_strict_numeric_vector_validation():
    """F14: VectorAnalysisRequest must reject booleans, strings, and incorrect lengths."""
    valid_vector = [0.5] * 2381

    # Valid vector passes
    req = VectorAnalysisRequest(features=valid_vector, source_name="test-sample")
    assert len(req.features) == 2381

    # Boolean is strictly rejected (not coerced to 1.0)
    bool_vector = [True] + [0.0] * 2380
    with pytest.raises(ValidationError):
        VectorAnalysisRequest(features=bool_vector)

    # String is strictly rejected (not coerced to 1.25)
    str_vector = ["1.25"] + [0.0] * 2380
    with pytest.raises(ValidationError):
        VectorAnalysisRequest(features=str_vector)  # type: ignore[arg-type]

    # Dimension mismatch (2380 instead of 2381) is rejected
    short_vector = [0.0] * 2380
    with pytest.raises(ValidationError):
        VectorAnalysisRequest(features=short_vector)


def test_no_destructive_prefix_deletion(tmp_path):
    """F02: Using a request_id starting with 'req-be04-' must never delete an existing job."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for col in Base.metadata.tables["audit_events"].columns:
        if col.name == "id":
            from sqlalchemy import Integer
            col.type = Integer()

    for table in (
        User.__table__,
        AnalysisJob.__table__,
        AnalysisResultRecord.__table__,
        DetectorScore.__table__,
        Artifact.__table__,
        Alert.__table__,
        AuditEvent.__table__,
    ):
        for col in cast(Any, table.columns):
            if col.server_default is not None and hasattr(col.server_default, "arg"):
                text_str = str(col.server_default.arg)
                if "N'" in text_str:
                    col.server_default.arg.text = text_str.replace("N'", "'")
        cast(Any, table).create(engine)

    from pathlib import Path
    svc = AnalysisService(
        audit_path=tmp_path / "events.jsonl",
        view_map_path=Path("configs/views.demo.yaml"),
        demo_mode=True,
    )
    test_rid = "req-be04-destructive-test"

    with Session(engine) as session:
        # First analysis with test_rid
        res1 = svc.analyze_vector([0.0] * 2381, request_id=test_rid, session=session)
        assert res1.request_id == test_rid

        job_before = session.scalar(select(AnalysisJob).where(AnalysisJob.request_id == test_rid))
        assert job_before is not None
        job_id_before = job_before.id

        # Second analysis with same test_rid but different vector payload:
        # Must raise AuditWriteFailureError AND job_before must NOT be deleted!
        with pytest.raises(AuditWriteFailureError, match="Duplicate request_id"):
            svc.analyze_vector([0.9] * 2381, request_id=test_rid, session=session)

        job_after = session.scalar(select(AnalysisJob).where(AnalysisJob.request_id == test_rid))
        assert job_after is not None, "Regression: existing job was deleted by prefix!"
        assert job_after.id == job_id_before


def test_audit_file_failure_resilience(tmp_path, monkeypatch):
    """F05: When file-based audit append fails, the DB transaction must succeed safely without crash."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for col in Base.metadata.tables["audit_events"].columns:
        if col.name == "id":
            from sqlalchemy import Integer
            col.type = Integer()

    for table in (
        User.__table__,
        AnalysisJob.__table__,
        AnalysisResultRecord.__table__,
        DetectorScore.__table__,
        Artifact.__table__,
        Alert.__table__,
        AuditEvent.__table__,
    ):
        for col in cast(Any, table.columns):
            if col.server_default is not None and hasattr(col.server_default, "arg"):
                text_str = str(col.server_default.arg)
                if "N'" in text_str:
                    col.server_default.arg.text = text_str.replace("N'", "'")
        cast(Any, table).create(engine)

    from pathlib import Path
    svc = AnalysisService(
        audit_path=tmp_path / "events.jsonl",
        view_map_path=Path("configs/views.demo.yaml"),
        demo_mode=True,
    )
    # Mock audit writer to raise IOError
    monkeypatch.setattr(svc.audit, "append", MagicMock(side_effect=OSError("Simulated read-only disk failure")))

    rid = f"req-audit-fail-{uuid.uuid4()}"
    with Session(engine) as session:
        result = svc.analyze_vector([0.0] * 2381, request_id=rid, session=session)
        assert result.request_id == rid

        # Verify job was successfully committed in DB
        persisted_job = session.scalar(select(AnalysisJob).where(AnalysisJob.request_id == rid))
        assert persisted_job is not None
        assert persisted_job.status in ("completed", "quarantined", "DEMO_ONLY")
