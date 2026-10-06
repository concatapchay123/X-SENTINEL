# PLAN-BE-12 — Jev AI Orchestration & Guardrails

## Objective
Coordinate explain/triage/compare/report while enforcing advisory-only semantics.

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit.
- Update baseline/change-control docs when assumptions change.

## Primary files
- `backend/src/x_sentinel/jev_ai/orchestrator.py`
- `backend/src/x_sentinel/jev_ai/schemas.py`

## Task sequence

1. Confirm upstream dependencies and unresolved P0 items.
2. Freeze interfaces/config/schema for this slice.
3. Implement or update skeleton/code/docs.
4. Add positive and negative tests.
5. Produce evidence/artifact hashes where applicable.
6. Update traceability/readiness.

## Acceptance
- prompt injection cases.
- authority-claim tests.
- response validation.


## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.
