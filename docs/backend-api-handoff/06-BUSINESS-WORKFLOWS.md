# X-SENTINEL V3 — BUSINESS WORKFLOWS

**Document ID:** `XS3-HANDOFF-06`  
**Version:** 3.0.0  
**Date:** 2026-10-16T14:04:49.547332+00:00  
**Classification:** Operational Sequences & Lifecycles  

---

## 1. End-to-End Threat Detection Workflow

Client submits vector -> FastAPI validates schema and token -> AnalysisService executes LightGBM and SHAP -> Detectors M1-M5 evaluate signals -> FusionEngine computes suspicion score -> Decision logic compares thresholds -> Canonical Evidence hash is generated -> Database atomic commit -> HTTP 200 response returned to client.

---

## 2. Security Alert Management Lifecycle

- State flow: `OPEN` -> `ACKNOWLEDGED` -> `RESOLVED` / `DISMISSED`.
- Terminal states (`RESOLVED`, `DISMISSED`) are immutable. Reopening returns HTTP 400 `XS_INVALID_TRANSITION`.
- Every transition emits an append-only `AuditEvent` with mandatory justification reason.
