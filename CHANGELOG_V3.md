# X-SENTINEL V3 Changelog

## Structural changes

- Split execution planning into `backend_database_ai` and `frontend` tracks.
- Preserved V2 PLAN-01…24 under `docs/plans/legacy_v2/`.
- Added V3 master dependency plan and migration map.
## BE-01: Repository, Environment & Configuration (PASS)

- Restored and verified 24 legacy V2 plans under `docs/plans/legacy_v2/`.
- Validated and froze configuration layer: `configs/jev_ai.yaml`, `.env.example`, `backend/src/x_sentinel/config.py`.
- Enforced strict dataset exclusion in `.gitignore` (`datasets/*`) and `.dockerignore` (`datasets/**`).
- Created `datasets/.gitkeep` and verified local user datasets (`ember2018`, `bodmas`) are preserved intact without deletion.
- Updated `scripts/baseline_audit.py` and `scripts/validate_v3_package.py` to support development working copy dataset preservation while enforcing strict distribution checks when requested.
- Implemented comprehensive BE-01 test suite (`backend/tests/test_be01_environment_config.py`).
- All 23 tests pass (2 skipped for live DB).

## BE-02: Microsoft SQL Server V3 Schema & Migration (PASS)

- Canonical Alembic migration head `0002_v3_jev_ai_audit` frozen and verified across Alembic, SQLAlchemy ORM models, and `schema.sql`.
- Completed DDL and index specifications for `jev_ai_runs` and `jev_ai_feedback` with strict audit constraints, `ON DELETE SET NULL` on job deletion to preserve audit logs, and `ON DELETE CASCADE` on feedback.
- Ensured strict scientific isolation: zero detector truth fields in Jev tables, zero Jev advisory fields in detector tables, non-contamination on Jev failure, and total exclusion of blind ground truth / hidden manifests.
- Implemented `scripts/check_schema_drift.py` verifying 0 schema differences across Alembic, `Base.metadata`, and live database.
- Implemented migration upgrade/downgrade suite (`tests/integration/test_migration_upgrade_downgrade.py`) validating both offline SQL generation and full live upgrade/downgrade cycles.
- Fixed default expected database revision in `tests/integration/test_migration_revision.py` to `0002_v3_jev_ai_audit`.
- Implemented `backend/tests/test_be02_schema_migrations.py` with 12 comprehensive unit and integration tests covering model metadata, check constraints, foreign keys, and failure isolation.
- All 40 automated tests pass with live SQL Server database (38 pass, 2 skipped when database unconfigured).

## Jev AI

- Changed AI/RAG baseline from `NOT APPLICABLE` to **OPTIONAL LOCAL COLLABORATOR**.
- Added LM Studio OpenAI-compatible integration contract.
- Added Jev AI context/data minimization rules.
- Added advisory-only decision boundary.
- Added auditable persistence model for Jev AI runs/feedback.
- Added Jev AI Python adapter/orchestrator skeleton.

## Database

- Adopted Microsoft SQL Server (MSSQL) via pyodbc/ODBC Driver 17/18 with Windows Authentication & SQL Server Auth support.
- New migration head `0002_v3_jev_ai_audit`.
- Adds `jev_ai_runs` and `jev_ai_feedback`.
- Blind evaluation ground truth remains isolated.

## Frontend

- V3 UI plan separates core analysis views from Jev AI explanation surfaces.
- UI must clearly distinguish **detector evidence** from **AI narrative**.

## Non-changes

- EMBER vector-first MVP remains canonical.
- Raw PE/LIEF remains Phase 2 until feature-equivalence is verified.
- M1–M5 and scientific gates remain authoritative.
- Jev AI does not replace LightGBM, SHAP, fusion, calibration or acceptance metrics.
