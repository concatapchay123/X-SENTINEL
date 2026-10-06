# PLAN-FE-06 — Jev AI Advisory Experience

## Objective
Add Explain/Triage/Report UI that is visually and semantically separated from detector truth.

## UX contract

- Backend is the source of truth.
- Canonical detector evidence and Jev AI narrative are never visually conflated.
- Loading, empty, disabled, error and retry states are explicit.
- Authorization is enforced by the server; UI only reflects capabilities.

## Primary files
- `frontend/`
- `docs/jev_ai/`

## Task sequence

1. Freeze API fixture/contract.
2. Implement view/state/components.
3. Add edge/error/permission states.
4. Add E2E or component checks.
5. Validate wording and evidence provenance.

## Acceptance
- AI unavailable does not hide result.
- model/run metadata shown.
- advisory label persistent.

