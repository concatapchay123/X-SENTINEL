# PLAN-BE-18 — Docker, CI & Deployment

## Status: COMPLETE

## Objective
Ship deterministic containers, migrations, staging checks and rollback tuple.

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit.
- Update baseline/change-control docs when assumptions change.

## Primary files
- `docker-compose.yml`
- `infrastructure/docker/backend.Dockerfile`
- `infrastructure/docker/frontend.Dockerfile`
- `.dockerignore`
- `.github/workflows/ci.yml`
- `scripts/migration_gate.py`
- `scripts/verify_release_tuple.py`
- `scripts/release_gate.py`
- `docs/runbooks/DEPLOYMENT_RUNBOOK.md`
- `docs/runbooks/ROLLBACK_RUNBOOK.md`
- `docs/release/RELEASE_CHECKLIST.md`
- `artifacts/release/release_tuple.json`
- `artifacts/release/RELEASE_MANIFEST.md`
- `artifacts/release/release_checklist.json`
- `tests/deployment/*`

## Task sequence

1. Confirm upstream dependencies and unresolved P0 items. [COMPLETED]
2. Freeze interfaces/config/schema for this slice. [COMPLETED]
3. Implement or update skeleton/code/docs. [COMPLETED]
4. Add positive and negative tests. [COMPLETED]
5. Produce evidence/artifact hashes where applicable. [COMPLETED]
6. Update traceability/readiness. [COMPLETED]

## Acceptance
- build test: Deterministic multi-stage Docker builds with non-root UID 10001, native scientific libraries (LightGBM, SHAP, ODBC), and passing `/health` and `/ready` probes. [VERIFIED]
- migration gate: Preflight and post-migration validation gate enforcing single head `0002_v3_jev_ai_audit`, 13 canonical tables, zero forbidden objects, dialect checks, and automated pre-migration backup gate (`scripts/migration_gate.py`). [VERIFIED]
- release checklist: Formally validated 10-gate release checklist (`scripts/release_gate.py` -> `docs/release/RELEASE_CHECKLIST.md` and `artifacts/release/release_checklist.json`) backed by cryptographic release tuple SHA-256 digest (`scripts/verify_release_tuple.py`). [VERIFIED]

## Done definition

No silent TBDs, no undocumented schema/API changes, 944/944 automated tests pass (918 upstream regression + 26 deployment), and outputs are traceable to versioned config/code.
