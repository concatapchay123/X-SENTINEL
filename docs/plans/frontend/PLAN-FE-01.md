# PLAN-FE-01 — Frontend Foundation & Navigation

## Objective
Establish UI structure, routing/navigation, environment/config and common components.

## UX contract

- Backend is the source of truth.
- Canonical detector evidence and Jev AI narrative are never visually conflated.
- Loading, empty, disabled, error and retry states are explicit.
- Authorization is enforced by the server; UI only reflects capabilities.

## Primary files
- `frontend/app.py`
- `frontend/README.md`

## Task sequence

1. Freeze API fixture/contract.
2. Implement view/state/components.
3. Add edge/error/permission states.
4. Add E2E or component checks.
5. Validate wording and evidence provenance.

## Acceptance
- app starts.
- status shell renders.
- demo mode visible.

