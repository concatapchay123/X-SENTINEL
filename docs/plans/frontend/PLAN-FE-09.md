# PLAN-FE-09 — UX, Security & Accessibility Hardening

## Objective
Harden copy, confirmation, authorization states, accessibility and sensitive-data display.

## UX contract

- Backend is the source of truth.
- Canonical detector evidence and Jev AI narrative are never visually conflated.
- Loading, empty, disabled, error and retry states are explicit.
- Authorization is enforced by the server; UI only reflects capabilities.

## Primary files
- `frontend/`

## Task sequence

1. Freeze API fixture/contract.
2. Implement view/state/components.
3. Add edge/error/permission states.
4. Add E2E or component checks.
5. Validate wording and evidence provenance.

## Acceptance
- keyboard/accessibility checks.
- no secret rendering.
- server auth respected.

