# PLAN-BE-07 — Fusion, D0/D1 Calibration & Decision

## Objective
Version fusion strategy, thresholds and decision policy.

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit.
- Update baseline/change-control docs when assumptions change.

## Primary files
- `backend/src/x_sentinel/fusion/*`

## Task sequence

1. Confirm upstream dependencies and unresolved P0 items.
2. Freeze interfaces/config/schema for this slice.
3. Implement or update skeleton/code/docs.
4. Add positive and negative tests.
5. Produce evidence/artifact hashes where applicable.
6. Update traceability/readiness.

## Acceptance
- calibration test.
- threshold provenance.
- decision golden cases.


## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.
