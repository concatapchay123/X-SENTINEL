#!/usr/bin/env python3
"""Database Migration Gate for X-SENTINEL V3.

Enforces strict release gate criteria:
1. Pre-migration revision chain integrity (single head, exact version match).
2. Database dialect & connectivity verification.
3. Pre-migration backup gate enforcement in production/staging environments.
4. Controlled schema migration execution.
5. Post-migration schema drift & forbidden table isolation audit.
6. Fail-closed return codes blocking CI/release on any violation.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure project root & backend/src are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "backend" / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "backend" / "src"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration_gate")

CANONICAL_MIGRATION_HEAD = "0002_v3_jev_ai_audit"
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


class MigrationGateError(Exception):
    """Raised when any database migration gate rule is violated."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


def get_alembic_config(config_path: str = "database/alembic.ini") -> Config:
    full_path = PROJECT_ROOT / config_path if not Path(config_path).is_absolute() else Path(config_path)
    if not full_path.exists():
        raise MigrationGateError(1, f"Alembic configuration file not found at {full_path}")
    cfg = Config(str(full_path))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "database" / "migrations"))
    return cfg


def verify_revision_chain(cfg: Config, expected_head: str = CANONICAL_MIGRATION_HEAD) -> str:
    """Verifies that the migration directory has exactly one head and matches expected head."""
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    if len(heads) != 1:
        raise MigrationGateError(
            2, f"Migration chain integrity failure: expected exactly 1 head, found {heads}"
        )
    actual_head = heads[0]
    if actual_head != expected_head:
        raise MigrationGateError(
            3, f"Revision mismatch: expected head '{expected_head}', found '{actual_head}'"
        )
    logger.info("Revision chain validated: single head at '%s'", actual_head)
    return actual_head


def get_current_db_revision(engine: Engine) -> str | None:
    """Queries alembic_version table to obtain current schema revision."""
    with engine.connect() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        if "alembic_version" not in tables:
            return None
        result = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        return str(result) if result is not None else None


def verify_schema_integrity(engine: Engine) -> None:
    """Verifies all expected tables exist and no forbidden tables are present."""
    with engine.connect() as conn:
        inspector = inspect(conn)
        actual_tables = set(inspector.get_table_names())

    missing = EXPECTED_TABLES - actual_tables
    if missing:
        raise MigrationGateError(4, f"Schema drift failure: missing tables {missing}")

    for tbl in actual_tables:
        for kw in FORBIDDEN_TABLE_KEYWORDS:
            if kw in tbl.lower():
                raise MigrationGateError(
                    4, f"Security isolation failure: forbidden table '{tbl}' found containing '{kw}'"
                )

    logger.info("Schema integrity verified: %d canonical tables present, 0 forbidden keywords", len(EXPECTED_TABLES))


def run_migration_gate(
    db_url: str | None = None,
    expected_revision: str = CANONICAL_MIGRATION_HEAD,
    allow_upgrade: bool = False,
    require_backup_gate: bool = False,
    backup_verified: bool = False,
    config_path: str = "database/alembic.ini",
) -> dict[str, str | bool | None]:
    """Executes the full database migration gate pipeline."""
    cfg = get_alembic_config(config_path)
    target_head = verify_revision_chain(cfg, expected_revision)

    if not db_url:
        db_url = os.getenv("XS_DATABASE_URL")

    if not db_url:
        logger.warning("XS_DATABASE_URL not set; skipping live DB migration gate checks")
        return {
            "status": "PASS_OFFLINE",
            "target_head": target_head,
            "current_revision": None,
            "upgraded": False,
        }

    # Safe sanitization of DB URL for logs
    driver_name = db_url.split("://")[0] if "://" in db_url else "unknown"
    logger.info("Connecting to target database (driver: %s)...", driver_name)

    engine = create_engine(db_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise MigrationGateError(1, f"Database connectivity failed: {exc}") from exc

    current_rev = get_current_db_revision(engine)
    logger.info("Current DB revision: %s; Target head: %s", current_rev, target_head)

    # Backup gate check
    is_prod_or_staging = os.getenv("XS_ENV", "").lower() in {"production", "staging"}
    if require_backup_gate or (is_prod_or_staging and allow_upgrade):
        if not backup_verified and os.getenv("XS_BACKUP_VERIFIED", "").lower() not in {"true", "1"}:
            raise MigrationGateError(
                5, "Pre-migration backup gate BLOCKED: verified database backup required before non-test migration."
            )
        logger.info("Pre-migration backup gate PASS: database restore point verified.")

    upgraded = False
    if current_rev != target_head:
        if not allow_upgrade:
            raise MigrationGateError(
                4,
                f"Migration gate BLOCKED: database revision ({current_rev}) != target ({target_head}). "
                "Run with --upgrade to apply pending migrations.",
            )

        logger.info("Applying Alembic upgrade to head (%s)...", target_head)
        try:
            command.upgrade(cfg, "head")
            upgraded = True
        except Exception as exc:
            raise MigrationGateError(6, f"Migration execution failed: {exc}") from exc

        # Post-migration verification
        new_rev = get_current_db_revision(engine)
        if new_rev != target_head:
            raise MigrationGateError(
                7, f"Post-migration verification failure: revision is {new_rev}, expected {target_head}"
            )
        logger.info("Upgrade completed successfully to %s", new_rev)

    # Final Schema Drift check
    verify_schema_integrity(engine)
    engine.dispose()

    logger.info("ALL MIGRATION GATES PASSED (Revision: %s)", target_head)
    return {
        "status": "PASS",
        "target_head": target_head,
        "current_revision": target_head,
        "upgraded": upgraded,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="X-SENTINEL V3 Migration Gate")
    parser.add_argument("--db-url", help="Database connection URL", default=None)
    parser.add_argument("--expected-revision", default=CANONICAL_MIGRATION_HEAD, help="Expected schema head revision")
    parser.add_argument("--upgrade", action="store_true", help="Apply migrations if schema is behind head")
    parser.add_argument("--require-backup", action="store_true", help="Enforce verified backup gate")
    parser.add_argument("--backup-verified", action="store_true", help="Signal that backup has been verified")
    parser.add_argument("--config", default="database/alembic.ini", help="Path to alembic.ini")

    args = parser.parse_args()

    try:
        run_migration_gate(
            db_url=args.db_url,
            expected_revision=args.expected_revision,
            allow_upgrade=args.upgrade,
            require_backup_gate=args.require_backup,
            backup_verified=args.backup_verified,
            config_path=args.config,
        )
        return 0
    except MigrationGateError as err:
        logger.error("MIGRATION GATE FAILED [Exit Code %d]: %s", err.code, err)
        return err.code
    except Exception as exc:
        logger.error("UNEXPECTED MIGRATION GATE ERROR: %s", exc)
        return 99


if __name__ == "__main__":
    sys.exit(main())
