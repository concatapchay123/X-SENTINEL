# PLAN-BE-13 — Jev AI Persistence, API & Feedback

## Status: ACCEPTED (2026-10-13)

## Objective
Persist AI run metadata/output per retention policy and expose AI endpoints (`POST /v1/ai/explain`, `GET /v1/ai/runs`, `GET /v1/ai/runs/{run_id}`, `POST /v1/ai/runs/{run_id}/feedback`, `GET /v1/ai/runs/{run_id}/feedback`, and gated `POST /v1/ai/docs/ask`).

## Scope

- Define and implement the canonical persistence, service, and REST API slice for Jev AI runs and analyst feedback.
- Keep detector science, platform persistence, and Jev AI authority boundaries explicit (`advisory_only: true`, zero mutation of Canonical Detector Truth or immutable evidence).
- Enforce non-blocking database transaction boundaries (no open DB transaction held during external LM Studio HTTP requests).
- Enforce server-side RBAC (`admin`, `analyst`), ownership/IDOR protection, and retention policy (`jev_ai_store_response_text`, `jev_ai_store_context_summary`).
- Synchronize OpenAPI 3.1.0 contracts and baseline traceability matrices.

## Primary files
- `backend/src/x_sentinel/database/models.py`
- `backend/src/x_sentinel/database/repositories/jev_ai.py`
- `backend/src/x_sentinel/services/jev_ai_service.py`
- `backend/src/x_sentinel/api/schemas.py`
- `backend/src/x_sentinel/api/routes.py`
- `backend/src/x_sentinel/main.py`
- `backend/src/x_sentinel/security/auth.py`
- `backend/src/x_sentinel/config.py`
- `backend/tests/test_be13_jev_persistence_api_feedback.py`
- `docs/api/openapi.yaml`
- `docs/api/jev_ai_openapi_fragment.yaml`

## Task sequence

1. [x] Confirm upstream dependencies (`BE-02`, `BE-08`, `BE-09`, `BE-10`, `BE-11`, `BE-12`, `BE-12.5`) and unresolved P0 items.
2. [x] Freeze interfaces/config/schema (`JevAIRunRepository`, `JevAIFeedbackRepository`, `JevAIService`, Pydantic schemas, error taxonomy).
3. [x] Implement repository, service, API endpoints, validation handler, and OpenAPI docs.
4. [x] Add comprehensive positive and negative unit, integration, live SQL Server, transaction isolation, feedback validation, and RBAC tests (`58 tests` in `test_be13_jev_persistence_api_feedback.py`).
5. [x] Verify SHA-256 input/output digests and canonical evidence immutability.
6. [x] Update traceability and feature matrices (`17_TRACEABILITY_MATRIX.md`, `18_FEATURE_MATRIX.md`).

## Acceptance
- [x] **Transaction isolation**: Two-phase commit around external LM Studio calls (zero open DB transactions during HTTP calls); clean rollback on DB commit/write errors; immutable canonical detector truth & evidence under AI runtime failures and concurrency.
- [x] **Feedback validation**: Strict Pydantic (`extra="forbid"`) and repository validation (`rating` integer `1..5` rejecting booleans, `label` enum `{'helpful','not_helpful','incorrect','unsafe','unclear'}`, comment max length & control-char rejection, prompt-injection/blind-data/authority-override scanning, secret/path redaction, terminal-run check `409 XS_AI_RUN_NOT_TERMINAL`, duplicate feedback conflict `409 XS_DUPLICATE_FEEDBACK`).
- [x] **RBAC tests**: Server-side `require_roles(Role.ADMIN.value, Role.ANALYST.value)`, unauthenticated `401 XS_UNAUTHENTICATED`, invalid token `401 XS_INVALID_CREDENTIALS`, forbidden roles (`operator`, `evaluator`, inactive user) `403 XS_FORBIDDEN`, and cross-user IDOR protection across analysis jobs, AI runs, and feedback.

## Done definition

No silent TBDs, no undocumented schema/API changes, all tests pass (`test_be13_jev_persistence_api_feedback.py` + full repository test suite + live SQL Server schema drift check), and outputs are traceable to versioned config/code.

