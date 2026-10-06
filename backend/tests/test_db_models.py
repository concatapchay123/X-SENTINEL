from x_sentinel.database.base import Base
from x_sentinel.database import models  # noqa: F401


def test_canonical_table_set() -> None:
    expected = {
        "users", "roles", "user_roles", "model_versions", "analysis_jobs",
        "analysis_results", "detector_scores", "alerts", "artifacts",
        "audit_events", "experiment_runs", "jev_ai_runs", "jev_ai_feedback",
    }
    assert set(Base.metadata.tables) == expected


def test_blind_ground_truth_not_in_application_schema() -> None:
    names = {name.lower() for name in Base.metadata.tables}
    forbidden = {"ground_truth", "manifest", "blind_labels", "trigger_labels"}
    assert names.isdisjoint(forbidden)
