# 16 — MASTER IMPLEMENTATION PLAN — V3

Execution hierarchy remains:

`PROJECT → TRACK → PLAN → EPIC → FEATURE → TASK → FILE → TEST → ACCEPTANCE`.

V3 has two implementation tracks.

## Track A — Backend / Database / Detection / Jev AI

Detailed plans: `docs/plans/backend_database_ai/`.

Execution spine:

`BE-01 → BE-02 → BE-03 → BE-04 → BE-05 → BE-06 → BE-07 → BE-08 → BE-09 → BE-10 → BE-11 → BE-12 → BE-13 → BE-14 → BE-15 → BE-16 → BE-17 → BE-18 → BE-19 → BE-20`

Key gates:

- DB migration head before persistent API/history features.
- scientific detector formulas/config freeze before final E0–E5 acceptance.
- Jev AI is optional and cannot block detector readiness.
- raw PE remains Phase 2.

## Track B — Frontend

Detailed plans: `docs/plans/frontend/`.

Execution spine:

`FE-01 → FE-02 → FE-03 → FE-04 → FE-05 → FE-06 → FE-07 → FE-08 → FE-09 → FE-10`

Frontend can start after API contracts and mocked schemas are stable; it does not wait for all scientific experiments.

## Parallelization

- FE-01/02 can run in parallel with BE-03/04 once API schemas are frozen.
- FE-03/04 depend on BE-09 contracts, but can use fixtures/mocks first.
- FE-06 depends on BE-10/11/12 Jev contracts.
- Final FE-10 depends on backend integration, auth/RBAC decisions and acceptance environment.

## Legacy mapping

V2 PLAN-01…24 are preserved under `docs/plans/legacy_v2/`. See `docs/plans/V2_TO_V3_MAP.md`.

## Acceptance boundary

Jev AI quality metrics and operator usefulness are separate from detector scientific acceptance. A good Jev explanation cannot compensate for missing SC evidence; a Jev outage cannot invalidate an otherwise valid detector result.
