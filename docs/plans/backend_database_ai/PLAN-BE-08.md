# PLAN-BE-08 — Audit, Evidence & Artifact Contracts

## Objective
Persist immutable canonical evidence and artifact checksums.

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit.
- Update baseline/change-control docs when assumptions change.

## Primary files
- `backend/src/x_sentinel/audit/*`
- `backend/src/x_sentinel/database/repositories/*`
- `docs/baseline/27_EVIDENCE_SCHEMA.md`

## Task sequence

1. Confirm upstream dependencies and unresolved P0 items.
2. Freeze interfaces/config/schema for this slice.
3. Implement or update skeleton/code/docs.
4. Add positive and negative tests.
5. Produce evidence/artifact hashes where applicable.
6. Update traceability/readiness.

## Acceptance
- audit write failure test.
- evidence hash test.


## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.
