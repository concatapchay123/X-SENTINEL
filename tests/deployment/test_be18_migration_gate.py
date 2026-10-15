from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from x_sentinel.database.models import AnalysisJob, Base

import scripts.migration_gate as mg

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestMigrationGateRevisions:
    """Tests Alembic revision chain, head validation, and error detection."""

    def test_canonical_revision_chain_single_head(self) -> None:
        cfg = mg.get_alembic_config()
        head = mg.verify_revision_chain(cfg, expected_head="0002_v3_jev_ai_audit")
        assert head == "0002_v3_jev_ai_audit"

    def test_mismatched_expected_head_raises_gate_error(self) -> None:
        cfg = mg.get_alembic_config()
        with pytest.raises(mg.MigrationGateError) as exc_info:
            mg.verify_revision_chain(cfg, expected_head="0003_future_revision")
        assert exc_info.value.code == 3
        assert "Revision mismatch" in str(exc_info.value)

    def test_multiple_heads_detection_blocks_migration(self) -> None:
        cfg = mg.get_alembic_config()
        with patch.object(ScriptDirectory, "get_heads", return_value=["head_a", "head_b"]):
            with pytest.raises(mg.MigrationGateError) as exc_info:
                mg.verify_revision_chain(cfg)
            assert exc_info.value.code == 2
            assert "expected exactly 1 head" in str(exc_info.value)


class TestMigrationGateLiveLifecycle:
    """Tests migration gate execution, drift detection, backup gates, and data preservation."""

    @pytest.fixture
    def isolated_db(self, tmp_path: Path):
        db_file = tmp_path / "test_migration_gate.db"
        db_url = f"sqlite:///{db_file}"
        engine = create_engine(db_url)

        # Normalize SQL Server NVARCHAR default syntax for SQLite compatibility
        for col in Base.metadata.tables["audit_events"].columns:
            if col.name == "id":
                from sqlalchemy import Integer

                col.type = Integer()
        for table in Base.metadata.tables.values():
            for col in table.columns:
                default_arg = getattr(col.server_default, "arg", None)
                if default_arg is not None:
                    text_str = str(default_arg)
                    if "N'" in text_str and hasattr(default_arg, "text"):
                        default_arg.text = text_str.replace("N'", "'")

        # Create full metadata
        Base.metadata.create_all(engine)
        # Seed alembic_version table at head
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('0002_v3_jev_ai_audit')"))
            conn.commit()
        yield engine, db_url
        engine.dispose()

    def test_migration_gate_passes_at_head(self, isolated_db) -> None:
        _, db_url = isolated_db
        res = mg.run_migration_gate(db_url=db_url, allow_upgrade=False)
        assert res["status"] == "PASS"
        assert res["target_head"] == "0002_v3_jev_ai_audit"
        assert res["current_revision"] == "0002_v3_jev_ai_audit"
        assert res["upgraded"] is False

    def test_migration_gate_fails_closed_when_behind_head_and_upgrade_false(self, isolated_db) -> None:
        engine, db_url = isolated_db
        with engine.connect() as conn:
            conn.execute(text("UPDATE alembic_version SET version_num = '0001_v2_multiuser'"))
            conn.commit()

        with pytest.raises(mg.MigrationGateError) as exc_info:
            mg.run_migration_gate(db_url=db_url, allow_upgrade=False)
        assert exc_info.value.code == 4
        assert "Run with --upgrade to apply pending migrations" in str(exc_info.value)

    def test_schema_integrity_rejects_forbidden_tables(self, isolated_db) -> None:
        engine, _ = isolated_db
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE ground_truth_blind (id INTEGER PRIMARY KEY)"))
            conn.commit()

        with pytest.raises(mg.MigrationGateError) as exc_info:
            mg.verify_schema_integrity(engine)
        assert exc_info.value.code == 4
        assert "forbidden table" in str(exc_info.value).lower()

    def test_schema_integrity_rejects_missing_canonical_tables(self, isolated_db) -> None:
        engine, _ = isolated_db
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS jev_ai_runs"))
            conn.commit()

        with pytest.raises(mg.MigrationGateError) as exc_info:
            mg.verify_schema_integrity(engine)
        assert exc_info.value.code == 4
        assert "missing tables" in str(exc_info.value)

    def test_production_backup_gate_enforcement(self, isolated_db) -> None:
        _, db_url = isolated_db
        with patch.dict(os.environ, {"XS_ENV": "production", "XS_BACKUP_VERIFIED": "false"}):
            with pytest.raises(mg.MigrationGateError) as exc_info:
                mg.run_migration_gate(
                    db_url=db_url,
                    allow_upgrade=True,
                    require_backup_gate=True,
                    backup_verified=False,
                )
            assert exc_info.value.code == 5
            assert "Pre-migration backup gate BLOCKED" in str(exc_info.value)

    def test_data_preservation_across_migration(self, isolated_db) -> None:
        engine, db_url = isolated_db
        # Insert persistent record
        with Session(engine) as session:
            job = AnalysisJob(
                request_id="req-persist-test-01",
                status="completed",
                input_mode="vector",
                demo_mode=True,
            )
            session.add(job)
            session.commit()

        # Run migration gate (no-op at head)
        res = mg.run_migration_gate(db_url=db_url, allow_upgrade=True)
        assert res["status"] == "PASS"

        # Verify data untouched
        with Session(engine) as session:
            job_queried = session.query(AnalysisJob).filter_by(request_id="req-persist-test-01").first()
            assert job_queried is not None
            assert job_queried.status == "completed"
