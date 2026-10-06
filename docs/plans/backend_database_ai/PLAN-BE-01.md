# PLAN-BE-01 — Repository, Environment & Configuration

## Objective
Freeze V3 project layout, environment variables, dataset exclusion rules and config versioning.

## Status: PASS

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit.
- Update baseline/change-control docs when assumptions change.

## Primary files
- `README.md`
- `.env.example`
- `configs/jev_ai.yaml`
- `backend/src/x_sentinel/config.py`
- `.dockerignore`
- `datasets/.gitkeep`
- `scripts/baseline_audit.py`
- `scripts/validate_v3_package.py`
- `backend/tests/test_be01_environment_config.py`
- `docs/baseline/*`

## Task sequence

1. [x] Confirm upstream dependencies and unresolved P0 items.
2. [x] Freeze interfaces/config/schema for this slice.
3. [x] Implement or update skeleton/code/docs.
4. [x] Add positive and negative tests.
5. [x] Produce evidence/artifact hashes where applicable.
6. [x] Update traceability/readiness.

## Acceptance
- [x] baseline audit passes (`python scripts/baseline_audit.py` PASS: 19 core files, 20 BE plans, 10 FE plans, 24 legacy plans, local datasets preserved & excluded from Git/Docker).
- [x] datasets is empty in distribution / properly excluded by `.gitignore` (`datasets/*`) and `.dockerignore` (`datasets/**`), with `datasets/.gitkeep` maintained.
- [x] package validation passes (`python scripts/validate_v3_package.py`).
- [x] all targeted and regression tests pass (23 passed, 2 skipped for unconfigured live DB).

## Done definition
No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.

## Recommended next eligible plan
`BE-02` (PostgreSQL / SQL Server V3 schema/migrations).
