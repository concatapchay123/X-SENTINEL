# 17 — REQUIREMENT TRACEABILITY MATRIX — V3

| Requirement | Backend/DB | API | Frontend | Test/Plan | Status |
|---|---|---|---|---|---|
| OPS-001/002 | `x_sentinel/config.py`, `.env.example`, `configs/jev_ai.yaml` | config/status, health | N/A | BE-01 (`test_be01_environment_config.py`) | PASS |
| OPS-006 / FR-030 | `main.py`, `database/health.py`, `jev_ai/status.py` | health, ready, v1/ai/status | N/A | BE-03 (`test_be03_foundation_health_readiness.py`) | PASS |
| FR-001/002 | `data/schema.py` | analyze/vector | Analyze | BE-04 (`test_be04_domain_schema_views.py`) / FE-03 | BE PASS |
| FR-003 | `data/views.py` | result evidence | Cross-view | BE-04 (`test_be04_domain_schema_views.py`) / FE-05 | BE PASS |
| FR-004/005 | `model/*` | analyze result | score/SHAP | BE-05 / FE-04/05 | PARTIAL |
| FR-006..010 | `detection/*` (`m1_tadr`, `m2_strip`, `m3_view`, `m4_cross_view`, `m5_semantic`, `pipeline`) | signal payload | M1–M5 cards | BE-06 (`test_be06_m1..m5`, `test_be06_detector_pipeline`) / FE-04 | BE PASS |
| FR-011..013 | `fusion/*` (`engine.py`, `calibration.py`, `decision.py`, `config.py`) | canonical result | decision banner | BE-07 (`test_be07_calibration`, `test_be07_threshold_provenance`, `test_be07_fusion_engine`, `test_be07_decision_golden_cases`, `test_be07_integration`) / FE-04 | BE PASS |
| FR-014/015/025 | `audit/*`, `services/*`, `api/*`, `database/repositories/*` | REST contracts: analyze/history/alerts/evidence | history/export | BE-08 / BE-09 (`test_be08_*`, `test_be09_*`) / FE-07 | BE-09 PASS |
| FR-017/018 | `evaluation/*` (`protocol.py`, `metrics.py`, `statistics.py`, `blind.py`, `runner.py`) | evaluation/status | evaluation | BE-14 (`test_be14_threat_simulation_e0_e5_statistics.py`) / FE-08 | BE PASS (Candidate E0–E5; Strict Scientific Blocked by OQ-01/02) |
| FR-021..024 | DB/migrations (`0002_v3_jev_ai_audit.py`, `models.py`) | ready/status | status/admin | BE-02 (`test_be02_schema_migrations.py`, `test_migration_upgrade_downgrade.py`) | PASS |
| FR-026 / AI-001..010 | `jev_ai/*`, `services/jev_ai_service.py`, `database/repositories/jev_ai.py` | `/v1/ai/status`, `/v1/ai/explain`, `/v1/ai/runs`, `/v1/ai/docs/ask` | advisory panel | BE-10..13 (`test_be10_*`, `test_be11_*`, `test_be12_*`, `test_be13_*`) / FE-06 | BE PASS |
| FR-027/028 | Jev DB tables (`jev_ai_runs`, `jev_ai_feedback`), `JevAIRunRepository`, `JevAIFeedbackRepository` | `/v1/ai/runs`, `/v1/ai/runs/{run_id}`, `/v1/ai/runs/{run_id}/feedback` | AI metadata/feedback | BE-02 / BE-13 (`test_be13_jev_persistence_api_feedback.py`) / FE-06 | BE PASS |
| SEC-007 | `evaluation/blind.py` (`BlindCustodyGuard`, `BlindPredictionPackage`, `BlindEvaluator`), `jev_ai/guardrails.py` | N/A | N/A | BE-14 (`test_be14_threat_simulation_e0_e5_statistics.py`) / BE-15 | BE-14 PASS |
| SEC-008..010 | Jev guardrails (`jev_ai/guardrails.py`), RBAC & feedback sanitization (`jev_ai_service.py`, `repositories/jev_ai.py`) | AI errors (`XS_AI_*`, `XS_FEEDBACK_INVALID`, `XS_DUPLICATE_FEEDBACK`) | advisory/error UX | BE-11/12/13/15 (`test_be11_*`, `test_be12_*`, `test_be13_*`) / FE-06/09 | BE-11..13 PASS |
| FR-020 | `data/raw_pe.py` | analyze/file | gated upload | BE-19 | GATED |
