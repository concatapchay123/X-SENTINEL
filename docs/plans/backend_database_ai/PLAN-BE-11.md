# PLAN-BE-11 — Jev AI Context Builder & Data Contract

## Objective
Project canonical evidence through an allowlist, redact, cap and digest.

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit.
- Update baseline/change-control docs when assumptions change.

## Primary files
- `backend/src/x_sentinel/jev_ai/prompt_builder.py`
- `backend/src/x_sentinel/jev_ai/guardrails.py`

## Task sequence

1. Confirm upstream dependencies and unresolved P0 items.
2. Freeze interfaces/config/schema for this slice.
3. Implement or update skeleton/code/docs.
4. Add positive and negative tests.
5. Produce evidence/artifact hashes where applicable.
6. Update traceability/readiness.

## Acceptance
- forbidden key tests.
- size cap tests.
- blind-data negative tests.


## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.
