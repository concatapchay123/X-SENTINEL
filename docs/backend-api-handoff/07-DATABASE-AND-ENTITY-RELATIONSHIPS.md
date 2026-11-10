# X-SENTINEL V3 — DATABASE & ENTITY RELATIONSHIPS

**Document ID:** `XS3-HANDOFF-07`  
**Version:** 3.0.0  
**Date:** 2026-10-16T14:04:49.547332+00:00  
**Classification:** Database Architecture & Entity Models  

---

## 1. Canonical Table Catalog (13 Tables)

1. `users`: System users and service principals.
2. `roles`: Defined roles (operator, analyst, admin, evaluator).
3. `user_roles`: Many-to-many role assignments.
4. `model_versions`: Frozen model digests and configuration hashes.
5. `analysis_jobs`: Master record for analysis execution jobs.
6. `analysis_results`: Final malware score, suspicion score, decision, and result JSON.
7. `detector_scores`: Individual M1–M5 signal results and diagnostics.
8. `artifacts`: Stored raw evidence JSON, model exports, and checksums.
9. `alerts`: Security incidents triggered by detection thresholds.
10. `jev_ai_runs`: Persisted advisory AI workflow runs and prompt contexts.
11. `jev_ai_feedback`: Human analyst evaluation and ratings of AI runs.
12. `audit_events`: Append-only, immutable audit trail of all mutations.
13. `calibration_records`: Stored empirical FPR/TPR calibration curves.
