# PLAN-BE-04 — Domain, Input Schema & Semantic Views

## Objective
Validate 2,381 features and authoritative Structural/Behavioral/Metadata mapping.

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit.
- Update baseline/change-control docs when assumptions change.

## Primary files
- `backend/src/x_sentinel/data/schema.py`
- `backend/src/x_sentinel/data/views.py`
- `configs/views.*.yaml`

## Task sequence

1. Confirm upstream dependencies and unresolved P0 items.
2. Freeze interfaces/config/schema for this slice.
3. Implement or update skeleton/code/docs.
4. Add positive and negative tests.
5. Produce evidence/artifact hashes where applicable.
6. Update traceability/readiness.

## Acceptance
- schema tests.
- view mapping hash test.


## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.
