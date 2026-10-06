# PLAN-BE-02 — Microsoft SQL Server V3 Schema & Migration

## Objective
Upgrade canonical schema to include Jev AI audit/feedback without contaminating detector truth.

## Status: PASS

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit.
- Update baseline/change-control docs when assumptions change.

## Primary files
- `database/migrations/versions/0002_v3_jev_ai_audit.py`
- `backend/src/x_sentinel/database/models.py`
- `database/schema/schema.sql`
- `database/schema/DATA_DICTIONARY.md`
- `scripts/check_schema_drift.py`
- `backend/tests/test_be02_schema_migrations.py`
- `tests/integration/test_migration_upgrade_downgrade.py`
- `tests/integration/test_migration_revision.py`

## Task sequence

1. [x] Confirm upstream dependencies and unresolved P0 items (BE-01 PASS verified).
2. [x] Freeze interfaces/config/schema for this slice (`0002_v3_jev_ai_audit`, `Base.metadata`, `schema.sql`).
3. [x] Implement or update skeleton/code/docs (`schema.sql` indexes, `check_schema_drift.py`).
4. [x] Add positive and negative tests (12 tests in `test_be02_schema_migrations.py`, 3 tests in `test_migration_upgrade_downgrade.py`).
5. [x] Produce evidence/artifact hashes where applicable (zero schema drift, live & offline migration cycles PASS).
6. [x] Update traceability/readiness.

## Acceptance
- [x] upgrade/downgrade test (`tests/integration/test_migration_upgrade_downgrade.py` PASS: offline SQL generation + live migration cycle on scratch DB).
- [x] schema drift check (`scripts/check_schema_drift.py` PASS: 0 differences between Alembic, `Base.metadata`, and live DB).
- [x] all targeted and regression tests pass (40 passed with live DB / 38 passed, 2 skipped when unconfigured).

## Done definition
No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.

## Recommended next eligible plan
`BE-03` (Backend foundation/readiness).
