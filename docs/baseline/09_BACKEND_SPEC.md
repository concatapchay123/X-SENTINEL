# 09 — BACKEND SPEC — V3

## Stack

- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 2 + Alembic + Microsoft SQL Server (via pyodbc)
- NumPy/Pandas, LightGBM, SHAP, scikit-learn/SciPy
- httpx for local LM Studio calls
- YAML configuration

## Layering

### API
Transport validation, auth context, error mapping, request IDs. No detector formulas.

### Services
- `AnalysisService`: canonical analysis orchestration.
- `JevAIOrchestrator`: optional advisory analysis from canonical evidence.

### Data
2,381 feature validation, view mapping and approved context extraction.

### Model
LightGBM and SHAP only.

### Detection
M1–M5 only, common typed result contract.

### Fusion
Calibrated suspicion score, threshold and decision only.

### Persistence
Repository/session boundaries; no ad-hoc SQL in routes.

### Jev AI
- `JevAIClient`: OpenAI-compatible local HTTP adapter.
- `JevContextBuilder`: converts canonical result to minimized prompt context.
- `JevAIGuardrails`: blocks blind data/raw binary/unapproved fields.
- `JevAIOrchestrator`: handles modes, timeout, audit and failure isolation.

## Error taxonomy additions

- `XS_AI_DISABLED`
- `XS_AI_UNAVAILABLE`
- `XS_AI_CONTEXT_BLOCKED`
- `XS_AI_TIMEOUT`
- `XS_AI_RESPONSE_INVALID`

## Critical invariant

Jev AI cannot be called before a canonical detector result exists for `explain`, `triage`, or `report` modes. It cannot mutate that result afterward.

## Suggested V3 API surface

- `POST /v1/analyze/vector`
- `POST /v1/analyze/file` (Phase 2 only)
- `GET /v1/analysis/{id}`
- `GET /v1/analysis/{id}/evidence`
- `GET /v1/alerts`
- `GET /v1/ai/status`
- `POST /v1/ai/explain`
- `GET /v1/ai/runs/{id}`
- `POST /v1/ai/runs/{id}/feedback`

Jev endpoints are optional and return an explicit disabled/unavailable state without degrading detector endpoints.
