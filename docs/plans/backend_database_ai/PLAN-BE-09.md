# PLAN-BE-09 — Core API, History & Alerts

## Objective
Expose canonical analysis/history/alert/evidence contracts.

## Status: PASS

## Scope

- Expose canonical analysis/history/alert/evidence contracts via FastAPI REST endpoints.
- Maintain detector science, platform persistence and Jev AI authority boundaries explicit (Zero runtime AI/LLM dependencies).
- Update baseline/change-control docs when assumptions change.

## Primary files
- `backend/src/x_sentinel/api/routes.py`
- `backend/src/x_sentinel/api/schemas.py`
- `backend/src/x_sentinel/services/analysis_service.py`
- `backend/src/x_sentinel/services/history_service.py`
- `backend/src/x_sentinel/services/alert_service.py`
- `backend/src/x_sentinel/services/evidence_service.py`
- `backend/src/x_sentinel/security/auth.py`
- `backend/src/x_sentinel/database/repositories/alert.py`
- `backend/src/x_sentinel/database/repositories/analysis.py`
- `docs/api/openapi.yaml`
- `backend/tests/test_be09_openapi_contract.py`
- `backend/tests/test_be09_authorization.py`
- `backend/tests/test_be09_core_api.py`
- `backend/tests/test_be09_integration.py`

## Task sequence

1. [x] Confirm upstream dependencies and unresolved P0 items (BE-01 through BE-08 all verified; 383 baseline tests passing).
2. [x] Freeze interfaces/config/schema for this slice (`AnalysisResponse`, `AnalysisJobSummary`, `AnalysisHistoryListResponse`, `AnalysisDetailResponse`, `AlertSummary`, `AlertListResponse`, `AlertStatusUpdateRequest`, `CanonicalEvidenceResponse`, `Role`, `AuthUser`, `AlertRepository`).
3. [x] Implement or update skeleton/code/docs (`routes.py`, `schemas.py`, `auth.py`, `alert_service.py`, `history_service.py`, `evidence_service.py`, `analysis_service.py`, `alert.py`, `analysis.py`, `openapi.yaml`).
4. [x] Add positive and negative tests (34 targeted tests across 4 test suites: OpenAPI contract, Authorization, Core API, and Integration).
5. [x] Produce evidence/artifact hashes where applicable (`docs/api/openapi.yaml` 27,531 bytes, evidence hash integrity verified).
6. [x] Update traceability and readiness documentation (`PLAN-BE-09.md`, `17_TRACEABILITY_MATRIX.md`, `18_FEATURE_MATRIX.md`, `24_BASELINE_READINESS_REPORT.md`).

## Acceptance
- [x] OpenAPI contract tests:
  - Generated OpenAPI 3.1.0 schema generated cleanly without errors.
  - All 11 canonical endpoints registered (`GET /health`, `GET /ready`, `GET /v1/config/status`, `GET /v1/ai/status`, `POST /v1/analyze/vector`, `POST /v1/analyze/file`, `GET /v1/analysis`, `GET /v1/analysis/{analysis_id}`, `GET /v1/analysis/{analysis_id}/evidence`, `GET /v1/alerts`, `GET /v1/alerts/{alert_id}`, `PATCH /v1/alerts/{alert_id}`).
  - Request/response models validated under `components.schemas`.
  - HTTPBearer security scheme definition verified.
  - Unique operation IDs verified across all operations.
  - Frozen contracts preserved for health and readiness.
  - `docs/api/openapi.yaml` synchronized with active schema.
  - 7 passed tests in `backend/tests/test_be09_openapi_contract.py`.
- [x] Authorization tests when enabled:
  - When `api_auth_mode == "none"`: unauthenticated access allowed without credentials.
  - When `api_auth_mode == "bearer"`: missing Authorization header rejected with 401 `XS_UNAUTHENTICATED`.
  - Malformed or invalid bearer tokens rejected with 401 `XS_INVALID_CREDENTIALS`.
  - Role-based server-side authorization enforced:
    - Operator role forbidden from reading evidence (403 `XS_FORBIDDEN`) and mutating alert status (403 `XS_FORBIDDEN`).
    - Evaluator role forbidden from submitting vector analysis (403 `XS_FORBIDDEN`).
    - Analyst role permitted to submit analysis, view history, view alerts, and read evidence.
    - Admin role permitted across all endpoints.
  - Client-side header injection (`X-Role`, `X-User-Role`) rejected; server-side token validation authoritative.
  - 7 passed tests in `backend/tests/test_be09_authorization.py`.
- [x] Core API functional tests:
  - Analysis API: 2,381-vector analysis, signal calculations, input validation (422), duplicate request_id rejection (409), Phase 2 file disabled (501).
  - History API: list history, pagination limit/offset, filtering by status/decision/input_mode, detail retrieval by UUID and request_id, 404 for missing records.
  - Alerts API: list alerts, severity/status filters, alert detail retrieval, valid lifecycle state transitions (`open` -> `acknowledged` -> `resolved`), invalid transition rejection (400 `XS_INVALID_TRANSITION`), unknown status rejection (400), 404 for missing alerts.
  - Evidence API: read-only canonical evidence retrieval, SHA-256 hash verification, tamper detection triggering 409 `XS_EVIDENCE_INTEGRITY_MISMATCH`, 404 for missing evidence.
  - 18 passed tests in `backend/tests/test_be09_core_api.py`.
- [x] Integration & Live Microsoft SQL Server tests:
  - Complete end-to-end user workflow: analyze vector -> generate job & evidence -> create alert -> list history -> get detail -> patch alert lifecycle -> read & verify evidence -> tamper verification.
  - Live Microsoft SQL Server integration verified directly against active SQL Server instance (`0002_v3_jev_ai_audit` head).
  - 2 passed tests in `backend/tests/test_be09_integration.py`.

## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.

## Recommended next eligible plan
`BE-10` (Jev AI LM Studio Runtime Client).
