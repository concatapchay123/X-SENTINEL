from __future__ import annotations

# ruff: noqa: E402
import os
import sys
from pathlib import Path

# Ensure backend/src is on import path
ROOT = Path(__file__).resolve().parents[1]
backend_src = ROOT / "backend" / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from x_sentinel.database import models  # noqa: F401
from x_sentinel.database.base import Base

EXPECTED_TABLES = {
    "users",
    "roles",
    "user_roles",
    "model_versions",
    "analysis_jobs",
    "analysis_results",
    "detector_scores",
    "alerts",
    "artifacts",
    "audit_events",
    "experiment_runs",
    "jev_ai_runs",
    "jev_ai_feedback",
}

FORBIDDEN_TABLE_KEYWORDS = {"ground_truth", "manifest", "blind_labels", "trigger_labels"}

JEV_RUNS_EXPECTED_COLUMNS = {
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

JEV_FEEDBACK_EXPECTED_COLUMNS = {
    "id",
    "jev_ai_run_id",
    "user_id",
    "rating",
    "label",
    "comment",
    "created_at",
}


def check_alembic_heads(alembic_ini_path: Path) -> str:
    cfg = Config(str(alembic_ini_path))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    if len(heads) != 1:
        raise ValueError(f"Expected exactly 1 Alembic head, found: {heads}")
    if heads[0] != "0002_v3_jev_ai_audit":
        raise ValueError(f"Expected head 0002_v3_jev_ai_audit, found: {heads[0]}")
    return heads[0]


def check_metadata_tables() -> None:
    actual_tables = set(Base.metadata.tables.keys())
    if actual_tables != EXPECTED_TABLES:
        diff = actual_tables.symmetric_difference(EXPECTED_TABLES)
        raise ValueError(f"Metadata tables mismatch. Symmetric difference: {diff}")

    # Check forbidden keywords
    for table_name in actual_tables:
        for kw in FORBIDDEN_TABLE_KEYWORDS:
            if kw in table_name.lower():
                raise ValueError(f"Forbidden keyword '{kw}' found in table '{table_name}'")

    # Check jev_ai_runs columns
    runs_cols = set(Base.metadata.tables["jev_ai_runs"].columns.keys())
    if runs_cols != JEV_RUNS_EXPECTED_COLUMNS:
        diff = runs_cols.symmetric_difference(JEV_RUNS_EXPECTED_COLUMNS)
        raise ValueError(f"jev_ai_runs columns mismatch. Symmetric difference: {diff}")

    # Check jev_ai_feedback columns
    feedback_cols = set(Base.metadata.tables["jev_ai_feedback"].columns.keys())
    if feedback_cols != JEV_FEEDBACK_EXPECTED_COLUMNS:
        diff = feedback_cols.symmetric_difference(JEV_FEEDBACK_EXPECTED_COLUMNS)
        raise ValueError(f"jev_ai_feedback columns mismatch. Symmetric difference: {diff}")


def check_schema_sql(schema_sql_path: Path) -> None:
    if not schema_sql_path.exists():
        raise FileNotFoundError(f"schema.sql not found at {schema_sql_path}")
    content = schema_sql_path.read_text(encoding="utf-8").lower()
    for table in EXPECTED_TABLES:
        if f"create table {table}" not in content:
            raise ValueError(f"schema.sql missing CREATE TABLE statement for '{table}'")
    for kw in FORBIDDEN_TABLE_KEYWORDS:
        if f"create table {kw}" in content:
            raise ValueError(f"schema.sql contains forbidden table creation for '{kw}'")


def check_live_db_drift(url: str | None) -> list[tuple]:
    if not url:
        return []
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            diff = compare_metadata(ctx, Base.metadata)
            return list(diff)
    finally:
        engine.dispose()


def main() -> int:
    alembic_ini = ROOT / "database" / "alembic.ini"
    schema_sql = ROOT / "database" / "schema" / "schema.sql"

    print("Checking Alembic migration head...")
    head = check_alembic_heads(alembic_ini)
    print(f"  Alembic head OK: {head}")

    print("Checking SQLAlchemy Base.metadata tables and columns...")
    check_metadata_tables()
    print(f"  Base.metadata OK: all {len(EXPECTED_TABLES)} canonical tables and columns validated")

    print("Checking reference database/schema/schema.sql...")
    check_schema_sql(schema_sql)
    print("  schema.sql OK: all tables declared, forbidden keywords absent")

    db_url = os.getenv("XS_DATABASE_URL")
    if not db_url:
        default_url = (
            "mssql+pyodbc://localhost/xsentinel"
            "?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
        )
        try:
            eng = create_engine(default_url, pool_pre_ping=True)
            with eng.connect():
                db_url = default_url
            eng.dispose()
        except Exception:
            db_url = None

    if db_url:
        print("Checking schema drift against live database...")
        diff = check_live_db_drift(db_url)
        if diff:
            print(f"BLOCKED: Schema drift detected ({len(diff)} differences):")
            for item in diff:
                print(f"  - {item}")
            return 1
        print("  Live DB schema drift check: 0 differences (MATCH)")
    else:
        print("  Live DB check skipped (no database reachable)")

    print("SCHEMA DRIFT CHECK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
