# X-SENTINEL V3 — BACKEND SYSTEM ARCHITECTURE

**Document ID:** `XS3-HANDOFF-01`  
**Version:** 3.0.0  
**Date:** 2026-10-16T14:04:49.547332+00:00  
**Classification:** Architectural Blueprint & Layer Separation  

---

## 1. Layered Architecture

X-SENTINEL V3 follows an explicit, decoupled 4-tier architectural pattern:

```
+-------------------------------------------------------------------------+
|                         API Controllers / Routes                        |
|   (FastAPI APIRouter, DTO Validation, RBAC Auth, HTTP Error Envelope)   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                           Application Services                          |
| (AnalysisService, AlertService, HistoryService, EvidenceService, JevAI) |
+-------------------------------------------------------------------------+
                                    |
                   +----------------+----------------+
                   |                                 |
                   v                                 v
+------------------------------------+   +--------------------------------+
|            Domain Logic            |   |   Repositories / Persistence   |
| (M1-M5, Fusion, Calibration, SHAP, |   | (CanonicalEvidenceRepository,  |
|  PE Rules, Jev Prompt Guardrails)  |   |  JevFeedbackRepository, Session)|
+------------------------------------+   +--------------------------------+
                   |                                 |
                   +----------------+----------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  External & Infrastructure Runtime                      |
| (LightGBM Native, LM Studio HTTP, SQL Server / SQLite, File Artifacts)  |
+-------------------------------------------------------------------------+
```

### 1.1 Architectural Rules
- **Thin Controllers:** API routes contain zero business logic; they parse Pydantic DTOs, verify roles via dependency injection (`require_roles`), delegate to application services, and serialize response models.
- **Explicit Transaction Boundaries:** Database write operations use scoped SQLAlchemy sessions with atomic commit/rollback wrappers (`AuditWriteFailureError`).
- **Deterministic Scientific Core:** Detectors take pure Python primitives (float lists) and return immutable dataclasses (`SignalResult`, `DetectionPipelineResult`).
- **Advisory AI Isolation:** Jev AI requests are sandboxed via local loopback validation (`_validate_loopback_host`) and cannot mutate detection states.

---

## 2. Data Flow Architecture

### 2.1 Online Vector Analysis Pipeline
1. **Client Request:** `POST /v1/analyze/vector` with JSON payload `VectorAnalysisRequest`.
2. **Schema Gate:** Validates vector length (strictly 2,381 elements), finite float bounds (`np.isfinite`), and demo mode header.
3. **Model Scoring:** LightGBM evaluates the 2,381-dim vector to produce base `malware_score` between 0.0 and 1.0.
4. **SHAP Tree Explainer:** Computes local feature attribution values.
5. **Detector Evaluation:**
   - **M1 (TADR):** Evaluates Top-k feature attribution dominance ratio.
   - **M2 (STRIP):** Blends vector with benign baselines (alpha=0.5), calculates Shannon entropy of predictions.
   - **M3 (View Concentration):** Measures attribution entropy across Byte, Structural, and Behavioral views.
   - **M4 (Disagreement):** Symmetric cross-view prediction discordance.
   - **M5 (Semantic Plausibility):** Verifies physical PE structural invariants (headers, sections, imports).
6. **Fusion & Calibration:** Combines five detector anomaly scores into `suspicion_score` and checks thresholds (D0 Alert, D1 Quarantine).
7. **Canonical Evidence Seal:** Hashes full state tuple (input, scores, SHAP, timestamps, model hashes) using HMAC/SHA-256.
8. **Atomic Persistence:** Persists `AnalysisJob`, `AnalysisResultRecord`, `DetectorScore`, `Artifact`, and `AuditEvent`.
9. **JSON Response:** Returns HTTP 200 `AnalysisResponse` within 50ms.
