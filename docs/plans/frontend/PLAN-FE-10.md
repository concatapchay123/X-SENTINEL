# PLAN-FE-10 — Frontend E2E, Performance & Acceptance

## Objective
Run full operator journeys with backend, DB and optional local AI.

## UX contract

- Backend is the source of truth.
- Canonical detector evidence and Jev AI narrative are never visually conflated.
- Loading, empty, disabled, error and retry states are explicit.
- Authorization is enforced by the server; UI only reflects capabilities.

## Primary files
- `tests/e2e/`
- `frontend/`

## Task sequence

1. Freeze API fixture/contract.
2. Implement view/state/components.
3. Add edge/error/permission states.
4. Add E2E or component checks.
5. Validate wording and evidence provenance.

## Acceptance
- analyze->result->AI->history flow.
- AI outage path.
- performance report.

