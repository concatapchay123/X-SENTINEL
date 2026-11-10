# X-SENTINEL V3 — COMPLETE BACKEND FEATURE INVENTORY

**Document ID:** `XS3-HANDOFF-02`  
**Version:** 3.0.0  
**Date:** 2026-10-16T14:04:49.547332+00:00  
**Classification:** Functional Capability Catalog  

---

## Comprehensive Feature Matrix

| Feature ID | Feature Name | Domain | Primary API Endpoint | Allowed Roles | DB Tables Involved | Test Coverage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FEAT-SYS-01** | Basic Health Probe | System | `GET /health` | Public / All | None | `test_be03_foundation_health_readiness.py` |
| **FEAT-SYS-02** | Readiness & Blockers Check | System | `GET /ready` | Public / All | None (DB ping) | `test_be03_foundation_health_readiness.py` |
| **FEAT-SYS-03** | System Configuration Status | System | `GET /v1/config/status` | Public / All | None (DB revision) | `test_be03_foundation_health_readiness.py` |
| **FEAT-SYS-04** | Prometheus Telemetry Export | Monitoring | `GET /metrics` | Admin / Scraper | None (Memory Registry) | `test_be17_observability.py` |
| **FEAT-DET-01** | EMBER Vector Analysis | Detection | `POST /v1/analyze/vector`| Operator, Analyst, Admin | `analysis_jobs`, `analysis_results`, `detector_scores`, `artifacts`, `audit_events` | `test_be09_core_api.py`, `test_be06_detector_pipeline.py` |
| **FEAT-DET-02** | Raw PE Ingestion (Fail-Closed) | Detection | `POST /v1/analyze/file` | Admin / Evaluator | None (HTTP 501) | `test_raw_pe_disabled.py` |
| **FEAT-DET-03** | M1 Top-k TADR Evaluation | Scientific Core | Internal Service | N/A (Embedded) | `detector_scores` | `test_be06_m1_tadr.py` |
| **FEAT-DET-04** | M2 Tabular STRIP Evaluation | Scientific Core | Internal Service | N/A (Embedded) | `detector_scores` | `test_be06_m2_strip.py` |
| **FEAT-DET-05** | M3 View Concentration | Scientific Core | Internal Service | N/A (Embedded) | `detector_scores` | `test_be06_m3_view.py` |
| **FEAT-DET-06** | M4 Cross-View Disagreement | Scientific Core | Internal Service | N/A (Embedded) | `detector_scores` | `test_be06_m4_cross_view.py` |
| **FEAT-DET-07** | M5 PE Semantic Invariants | Scientific Core | Internal Service | N/A (Embedded) | `detector_scores` | `test_be06_m5_semantic.py` |
| **FEAT-DET-08** | Dual-Threshold Decision Fusion| Scientific Core | Internal Service | N/A (Embedded) | `analysis_results` | `test_be07_fusion_engine.py` |
| **FEAT-HIST-01**| Analysis History Pagination | History | `GET /v1/analysis` | Analyst, Admin | `analysis_jobs`, `analysis_results` | `test_be09_core_api.py` |
| **FEAT-HIST-02**| Analysis Result Detail Query | History | `GET /v1/analysis/{<built-in function id>}` | Analyst, Admin | `analysis_jobs`, `analysis_results`, `detector_scores` | `test_be09_core_api.py` |
| **FEAT-EVID-01**| Canonical Evidence Verification| Evidence | `GET /v1/analysis/{<built-in function id>}/evidence` | Analyst, Admin | `artifacts`, `analysis_jobs`, `analysis_results` | `test_be08_canonical_evidence_contract.py` |
| **FEAT-ALRT-01**| Security Alert Listing & Filter| Alerts | `GET /v1/alerts` | Analyst, Admin | `alerts` | `test_be09_core_api.py` |
| **FEAT-ALRT-02**| Security Alert Detail Query | Alerts | `GET /v1/alerts/{<built-in function id>}` | Analyst, Admin | `alerts` | `test_be09_core_api.py` |
| **FEAT-ALRT-03**| Alert Lifecycle Transition | Alerts | `PATCH /v1/alerts/{<built-in function id>}` | Analyst, Admin | `alerts`, `audit_events` | `test_be09_core_api.py` |
| **FEAT-JEV-01** | Jev AI Runtime Status Check | AI Advisory | `GET /v1/ai/status` | Operator, Analyst, Admin | None (Local socket check) | `test_be10_jev_ai_runtime_client.py` |
| **FEAT-JEV-02** | Advisory Workflow Execution | AI Advisory | `POST /v1/ai/explain` | Analyst, Admin | `jev_ai_runs`, `audit_events` | `test_be12_jev_orchestration_guardrails.py` |
| **FEAT-JEV-03** | Persisted AI Run Listing | AI Advisory | `GET /v1/ai/runs` | Analyst, Admin | `jev_ai_runs` | `test_be13_jev_persistence_api_feedback.py` |
| **FEAT-JEV-04** | Persisted AI Run Query by ID | AI Advisory | `GET /v1/ai/runs/{<built-in function id>}` | Analyst, Admin | `jev_ai_runs` | `test_be13_jev_persistence_api_feedback.py` |
| **FEAT-JEV-05** | Record Analyst AI Feedback | AI Advisory | `POST /v1/ai/runs/{<built-in function id>}/feedback` | Analyst, Admin | `jev_ai_feedback`, `audit_events` | `test_be13_jev_persistence_api_feedback.py` |
| **FEAT-JEV-06** | List Feedback for AI Run | AI Advisory | `GET /v1/ai/runs/{<built-in function id>}/feedback` | Analyst, Admin | `jev_ai_feedback` | `test_be13_jev_persistence_api_feedback.py` |
| **FEAT-JEV-07** | Repository Documentation QA | AI Advisory | `POST /v1/ai/docs/ask` | Analyst, Admin | None (Gated phase 2) | `test_be12_jev_orchestration_guardrails.py` |
