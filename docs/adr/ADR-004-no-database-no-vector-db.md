# ADR-004 — Filesystem-only persistence in V1 — SUPERSEDED

**Status:** SUPERSEDED by ADR-007 for relational persistence. The vector-DB/RAG portion remains valid: Vector DB is still NOT APPLICABLE.

## Context
V1 source documents had no DB schema and audit was JSON-oriented.

## Prior decision
Use filesystem evidence artifacts and no relational DB for MVP.

## Superseding reason
The user subsequently made multi-user / cross-developer schema consistency an explicit requirement. That is sufficient to require centralized durable relational persistence plus migrations.
