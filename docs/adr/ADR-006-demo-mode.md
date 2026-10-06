# ADR-006 — Demo mode is non-scientific

## Context
A runnable skeleton helps frontend/backend integration before real model artifacts exist.

## Decision
Allow deterministic demo outputs only when `XS_DEMO_MODE=true`. All responses/audit records carry a demo flag and warning.

## Consequences
Demo artifacts are automatically rejected by scientific acceptance checks.
