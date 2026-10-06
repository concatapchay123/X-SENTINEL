# 10 — API CONTRACT — V3

REST is the canonical frontend/backend boundary.

## Core endpoints

### GET `/health`
Service liveness. Includes version/demo mode and whether Jev AI is configured enabled.

### GET `/ready`
Detector/platform readiness. DB revision mismatch may block readiness. **Jev AI availability does not block detector readiness.**

### GET `/v1/config/status`
Returns non-secret environment/demo/input/database and Jev config identity.

### POST `/v1/analyze/vector`
Analyze exactly one 2,381-feature vector. Returns canonical detector result.

### POST `/v1/analyze/file`
Phase 2 only; disabled until raw-PE equivalence gate.

### GET `/v1/analysis/{analysis_id}`
Planned V3 canonical result/history retrieval.

### GET `/v1/analysis/{analysis_id}/evidence`
Planned evidence metadata/download contract with authorization.

### GET `/v1/alerts`
Planned alert listing/filtering.

## Jev AI endpoints

### GET `/v1/ai/status`
Returns enabled state, advisory-only flag, configured model ID, prompt version and non-secret endpoint label. A failed LM Studio probe should return AI-unavailable state, not backend unready.

### POST `/v1/ai/explain`
Input references an existing canonical analysis ID plus `mode` and optional operator question. The backend fetches canonical evidence server-side; clients should not be allowed to forge detector facts.

Example request:

```json
{
  "analysis_id": "uuid",
  "mode": "explain",
  "question": "Why was this sample alerted?"
}
```

Example response envelope:

```json
{
  "run_id": "uuid",
  "analysis_id": "uuid",
  "status": "completed",
  "advisory_only": true,
  "model_id": "actual-lm-studio-model-id",
  "prompt_version": "jev-v3.0.0",
  "text": "...",
  "latency_ms": 1234.5
}
```

Errors include `XS_AI_DISABLED`, `XS_AI_UNAVAILABLE`, `XS_AI_CONTEXT_BLOCKED`, `XS_AI_TIMEOUT` and `XS_AI_RESPONSE_INVALID`.

### GET `/v1/ai/runs/{run_id}`
Read authorized AI run metadata/output subject to retention policy.

### POST `/v1/ai/runs/{run_id}/feedback`
Submit rating/label/comment. Feedback never mutates detector truth.

## Contract rule

Update baseline/API schema/tests before backend or frontend implementation changes. `docs/api/jev_ai_openapi_fragment.yaml` captures the V3 AI surface until merged into the canonical OpenAPI file.
