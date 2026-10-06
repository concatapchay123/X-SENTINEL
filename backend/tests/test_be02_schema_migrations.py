from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from x_sentinel.config import settings
from x_sentinel.database.base import Base
from x_sentinel.database.models import (
    AnalysisJob,
    AnalysisResultRecord,
    DetectorScore,
    JevAIFeedback,
    JevAIRun,
)


def _is_db_connected() -> bool:
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


db_available = _is_db_connected()


# ---------------------------------------------------------------------------
# Unit / Metadata tests (Offline, no DB required)
# ---------------------------------------------------------------------------


def test_jev_ai_runs_table_metadata() -> None:
    table = Base.metadata.tables["jev_ai_runs"]

    # Check columns exist
    expected_cols = {
        "id",
        "analysis_job_id",
        "requested_by_user_id",
        "mode",
        "status",
        "model_id",
        "endpoint_label",
        "prompt_version",
        "input_digest_sha256",
        "output_digest_sha256",
        "context_summary",
        "response_text",
        "latency_ms",
        "error_code",
        "error_message",
        "created_at",
        "completed_at",
    }
    assert set(table.columns.keys()) == expected_cols

    # Check nullability
    assert not table.columns["id"].nullable
    assert table.columns["analysis_job_id"].nullable
    assert table.columns["requested_by_user_id"].nullable
    assert not table.columns["mode"].nullable
    assert not table.columns["status"].nullable
    assert not table.columns["model_id"].nullable
    assert not table.columns["endpoint_label"].nullable
    assert not table.columns["prompt_version"].nullable
    assert not table.columns["input_digest_sha256"].nullable
    assert table.columns["output_digest_sha256"].nullable
    assert not table.columns["context_summary"].nullable
    assert table.columns["response_text"].nullable
    assert not table.columns["created_at"].nullable

    # Check Foreign Keys
    fks = {fk.target_fullname for fk in table.foreign_keys}
    assert "analysis_jobs.id" in fks
    assert "users.id" in fks

    # Check ondelete rules
    for fk in table.foreign_keys:
        if fk.target_fullname == "analysis_jobs.id":
            assert fk.ondelete == "SET NULL"
        elif fk.target_fullname == "users.id":
            assert fk.ondelete == "SET NULL"


def test_jev_ai_feedback_table_metadata() -> None:
    table = Base.metadata.tables["jev_ai_feedback"]

    expected_cols = {
        "id",
        "jev_ai_run_id",
        "user_id",
        "rating",
        "label",
        "comment",
        "created_at",
    }
    assert set(table.columns.keys()) == expected_cols

    assert not table.columns["id"].nullable
    assert not table.columns["jev_ai_run_id"].nullable
    assert table.columns["user_id"].nullable
    assert table.columns["rating"].nullable
    assert table.columns["label"].nullable
    assert table.columns["comment"].nullable
    assert not table.columns["created_at"].nullable

    fks = {fk.target_fullname: fk.ondelete for fk in table.foreign_keys}
    assert fks["jev_ai_runs.id"] == "CASCADE"
    assert fks["users.id"] == "SET NULL"


def test_scientific_isolation_boundaries() -> None:
    """Verifies Jev tables do not contain detector decision fields,
    and detector tables do not contain Jev fields.
    """
    jev_run_cols = set(Base.metadata.tables["jev_ai_runs"].columns.keys())
    jev_feedback_cols = set(Base.metadata.tables["jev_ai_feedback"].columns.keys())

    # Detector authority fields must NEVER exist in Jev tables
    detector_truth_fields = {
        "malware_score",
        "suspicion_score",
        "threshold",
        "decision",
        "detector_code",
        "score",
    }
    assert jev_run_cols.isdisjoint(detector_truth_fields)
    assert jev_feedback_cols.isdisjoint(detector_truth_fields)

    # Detector tables must not have Jev advisory fields
    detector_result_cols = set(Base.metadata.tables["analysis_results"].columns.keys())
    jev_fields = {"model_id", "prompt_version", "response_text", "endpoint_label", "feedback"}
    assert detector_result_cols.isdisjoint(jev_fields)


def test_blind_ground_truth_isolation() -> None:
    """Verifies that no hidden trigger manifests or blind ground truth exist in any table."""
    all_table_names = set(Base.metadata.tables.keys())
    forbidden = {"ground_truth", "manifest", "blind_labels", "trigger_labels"}
    for table_name in all_table_names:
        for kw in forbidden:
            assert kw not in table_name.lower()


# ---------------------------------------------------------------------------
# Database Integration tests (requires live DB)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not db_available, reason="live DB not reachable")
def test_positive_jev_ai_run_and_feedback_lifecycle() -> None:
    engine = create_engine(settings.database_url)
    req_id = f"test-req-{uuid.uuid4()}"
    run_id = uuid.uuid4()
    feedback_id = uuid.uuid4()

    with Session(engine) as session:
        # Create an AnalysisJob
        job = AnalysisJob(
            request_id=req_id,
            status="completed",
            input_mode="vector",
            demo_mode=True,
        )
        session.add(job)
        session.flush()
        job_id = job.id

        # Create JevAIRun attached to job
        jev_run = JevAIRun(
            id=run_id,
            analysis_job_id=job_id,
            mode="explain",
            status="completed",
            model_id="lm-studio-qwen-7b",
            endpoint_label="lm_studio_local",
            prompt_version="jev-v3.0.0",
            input_digest_sha256="a" * 64,
            output_digest_sha256="b" * 64,
            context_summary={"test": True},
            response_text="Advisory explanation: suspicious entropy observed in Section 2.",
            latency_ms=145.2,
        )
        session.add(jev_run)
        session.flush()

        # Create JevAIFeedback attached to run
        feedback = JevAIFeedback(
            id=feedback_id,
            jev_ai_run_id=jev_run.id,
            rating=5,
            label="helpful",
            comment="Clear and grounded explanation",
        )
        session.add(feedback)
        session.commit()

    # Query back and verify
    with Session(engine) as session:
        queried_run = session.get(JevAIRun, run_id)
        assert queried_run is not None
        assert queried_run.mode == "explain"
        assert queried_run.status == "completed"
        assert queried_run.response_text.startswith("Advisory explanation")

        queried_feedback = session.get(JevAIFeedback, feedback_id)
        assert queried_feedback is not None
        assert queried_feedback.rating == 5
        assert queried_feedback.label == "helpful"

        # Cleanup
        session.delete(queried_feedback)
        session.delete(queried_run)
        queried_job = session.get(AnalysisJob, job_id)
        if queried_job:
            session.delete(queried_job)
        session.commit()

    engine.dispose()


@pytest.mark.skipif(not db_available, reason="live DB not reachable")
def test_negative_jev_ai_run_invalid_mode() -> None:
    engine = create_engine(settings.database_url)
    with Session(engine) as session:
        invalid_run = JevAIRun(
            mode="unauthorized_mode",  # Invalid mode
            status="completed",
            model_id="test-model",
            prompt_version="v1",
            input_digest_sha256="c" * 64,
        )
        session.add(invalid_run)
        with pytest.raises(IntegrityError):
            session.commit()
    engine.dispose()


@pytest.mark.skipif(not db_available, reason="live DB not reachable")
def test_negative_jev_ai_run_invalid_status() -> None:
    engine = create_engine(settings.database_url)
    with Session(engine) as session:
        invalid_run = JevAIRun(
            mode="explain",
            status="invalid_status",  # Invalid status
            model_id="test-model",
            prompt_version="v1",
            input_digest_sha256="d" * 64,
        )
        session.add(invalid_run)
        with pytest.raises(IntegrityError):
            session.commit()
    engine.dispose()


@pytest.mark.skipif(not db_available, reason="live DB not reachable")
def test_negative_jev_feedback_invalid_rating() -> None:
    engine = create_engine(settings.database_url)
    run_id = uuid.uuid4()
    with Session(engine) as session:
        jev_run = JevAIRun(
            id=run_id,
            mode="explain",
            status="completed",
            model_id="test-model",
            prompt_version="v1",
            input_digest_sha256="e" * 64,
        )
        session.add(jev_run)
        session.flush()

        feedback = JevAIFeedback(
            jev_ai_run_id=run_id,
            rating=6,  # Invalid: must be 1..5
            label="helpful",
        )
        session.add(feedback)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    engine.dispose()


@pytest.mark.skipif(not db_available, reason="live DB not reachable")
def test_negative_jev_feedback_invalid_label() -> None:
    engine = create_engine(settings.database_url)
    run_id = uuid.uuid4()
    with Session(engine) as session:
        jev_run = JevAIRun(
            id=run_id,
            mode="explain",
            status="completed",
            model_id="test-model",
            prompt_version="v1",
            input_digest_sha256="f" * 64,
        )
        session.add(jev_run)
        session.flush()

        feedback = JevAIFeedback(
            jev_ai_run_id=run_id,
            rating=4,
            label="not_an_allowed_label",  # Invalid label
        )
        session.add(feedback)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    engine.dispose()


@pytest.mark.skipif(not db_available, reason="live DB not reachable")
def test_foreign_key_set_null_on_job_deletion() -> None:
    """When an AnalysisJob is deleted, JevAIRun.analysis_job_id becomes NULL,
    preserving audit history.
    """
    engine = create_engine(settings.database_url)
    req_id = f"delete-job-test-{uuid.uuid4()}"
    run_id = uuid.uuid4()

    with Session(engine) as session:
        job = AnalysisJob(
            request_id=req_id,
            status="completed",
            input_mode="vector",
            demo_mode=True,
        )
        session.add(job)
        session.flush()
        job_id = job.id

        run = JevAIRun(
            id=run_id,
            analysis_job_id=job_id,
            mode="triage",
            status="completed",
            model_id="test-model",
            prompt_version="v1",
            input_digest_sha256="1" * 64,
        )
        session.add(run)
        session.commit()

        # Delete AnalysisJob
        job_to_delete = session.get(AnalysisJob, job_id)
        if job_to_delete:
            session.delete(job_to_delete)
            session.commit()

    with Session(engine) as session:
        persisted_run = session.get(JevAIRun, run_id)
        assert persisted_run is not None
        assert persisted_run.analysis_job_id is None  # ON DELETE SET NULL verified!

        session.delete(persisted_run)
        session.commit()

    engine.dispose()


@pytest.mark.skipif(not db_available, reason="live DB not reachable")
def test_foreign_key_cascade_on_run_deletion() -> None:
    """When a JevAIRun is deleted, associated JevAIFeedback is deleted via CASCADE."""
    engine = create_engine(settings.database_url)
    run_id = uuid.uuid4()
    feedback_id = uuid.uuid4()

    with Session(engine) as session:
        run = JevAIRun(
            id=run_id,
            mode="report",
            status="completed",
            model_id="test-model",
            prompt_version="v1",
            input_digest_sha256="2" * 64,
        )
        session.add(run)
        session.flush()

        feedback = JevAIFeedback(
            id=feedback_id,
            jev_ai_run_id=run.id,
            rating=3,
            label="unclear",
        )
        session.add(feedback)
        session.commit()

        # Delete JevAIRun
        run_to_delete = session.get(JevAIRun, run_id)
        if run_to_delete:
            session.delete(run_to_delete)
            session.commit()

    with Session(engine) as session:
        assert session.get(JevAIRun, run_id) is None
        assert session.get(JevAIFeedback, feedback_id) is None  # CASCADE verified!

    engine.dispose()


@pytest.mark.skipif(not db_available, reason="live DB not reachable")
def test_detector_truth_uncontaminated_by_jev_failure() -> None:
    """Simulates an analysis result, followed by a failed Jev AI run.
    The detector result must remain intact and authoritative.
    """
    engine = create_engine(settings.database_url)
    req_id = f"detector-uncontam-{uuid.uuid4()}"
    run_id = uuid.uuid4()

    with Session(engine) as session:
        job = AnalysisJob(
            request_id=req_id,
            status="completed",
            input_mode="vector",
            demo_mode=True,
        )
        session.add(job)
        session.flush()
        job_id = job.id

        result = AnalysisResultRecord(
            analysis_job_id=job_id,
            malware_score=0.88,
            suspicion_score=0.92,
            threshold=0.50,
            decision="alert",
            latency_ms=8.5,
        )
        session.add(result)

        score = DetectorScore(
            analysis_job_id=job_id,
            detector_code="M1",
            score=0.88,
            diagnostics={"high_entropy": True},
        )
        session.add(score)
        session.commit()

        # Jev AI run fails
        failed_run = JevAIRun(
            id=run_id,
            analysis_job_id=job_id,
            mode="explain",
            status="failed",
            model_id="test-model",
            prompt_version="v1",
            input_digest_sha256="3" * 64,
            error_code="XS_AI_TIMEOUT",
            error_message="Local LM Studio request timed out after 60s",
        )
        session.add(failed_run)
        session.commit()

    # Verify detector result is completely untouched
    with Session(engine) as session:
        persisted_result = session.get(AnalysisResultRecord, job_id)
        assert persisted_result is not None
        assert persisted_result.decision == "alert"
        assert persisted_result.malware_score == 0.88
        assert persisted_result.suspicion_score == 0.92

        persisted_score = session.get(DetectorScore, (job_id, "M1"))
        assert persisted_score is not None
        assert persisted_score.score == 0.88

        persisted_failed_run = session.get(JevAIRun, run_id)
        assert persisted_failed_run.status == "failed"
        assert persisted_failed_run.error_code == "XS_AI_TIMEOUT"

        # Cleanup
        session.delete(persisted_failed_run)
        session.delete(persisted_score)
        session.delete(persisted_result)
        job_to_del = session.get(AnalysisJob, job_id)
        if job_to_del:
            session.delete(job_to_del)
        session.commit()

    engine.dispose()
