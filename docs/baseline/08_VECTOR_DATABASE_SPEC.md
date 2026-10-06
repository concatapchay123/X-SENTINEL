# 08 — VECTOR DATABASE / RETRIEVAL SPEC — V3

## Decision

A vector database is **NOT REQUIRED** for X-SENTINEL V3.

Jev AI operates on canonical structured evidence supplied directly by the backend. No embedding/vector retrieval is needed for detector operation or core AI explanation.

## Future document retrieval

If project-doc/runbook retrieval is added later:

- create an ADR;
- define source allowlist and access control;
- retain document provenance in outputs;
- evaluate retrieval quality/prompt injection;
- keep retrieval outside the detector path;
- do not index blind manifests or sensitive sample payloads.
