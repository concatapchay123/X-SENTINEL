# ADR-008 — Migration-first schema control

## Context
ORM-first coding by multiple agents can silently drift from actual databases.

## Decision
No persistent model change is accepted without a corresponding Alembic revision. CI runs `alembic check`; backend readiness compares current DB revision to the expected revision.

## Alternatives
Manual DDL and auto-create-on-start were rejected because they hide drift and are unsafe for shared environments.

## Consequences
Migrations are immutable after sharing/application. Destructive changes use expand-and-contract. Agents must report migration IDs in completion summaries.
