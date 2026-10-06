# PLAN-BE-10 — Jev AI LM Studio Runtime Client

## Objective
Implement local OpenAI-compatible client with configurable model/base URL/timeouts.

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit.
- Update baseline/change-control docs when assumptions change.

## Primary files
- `backend/src/x_sentinel/jev_ai/client.py`
- `configs/jev_ai.yaml`

## Task sequence

1. Confirm upstream dependencies and unresolved P0 items.
2. Freeze interfaces/config/schema for this slice.
3. Implement or update skeleton/code/docs.
4. Add positive and negative tests.
5. Produce evidence/artifact hashes where applicable.
6. Update traceability/readiness.

## Acceptance
- disabled mode.
- mocked success.
- timeout.
- network failure.


## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.
