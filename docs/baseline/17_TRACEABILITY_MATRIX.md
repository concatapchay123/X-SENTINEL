# 17 — REQUIREMENT TRACEABILITY MATRIX — V3

| Requirement | Backend/DB | API | Frontend | Test/Plan | Status |
|---|---|---|---|---|---|
| OPS-001/002 | `x_sentinel/config.py`, `.env.example`, `configs/jev_ai.yaml` | config/status, health | N/A | BE-01 (`test_be01_environment_config.py`) | PASS |
| OPS-006 / FR-030 | `main.py`, `database/health.py`, `jev_ai/status.py` | health, ready, v1/ai/status | N/A | BE-03 (`test_be03_foundation_health_readiness.py`) | PASS |
| FR-001/002 | `data/schema.py` | analyze/vector | Analyze | BE-04 / FE-03 | PARTIAL |
| FR-003 | `data/views.py` | result evidence | Cross-view | BE-04 / FE-05 | PARTIAL |
| FR-004/005 | `model/*` | analyze result | score/SHAP | BE-05 / FE-04/05 | PARTIAL |
| FR-006..010 | `detection/*` | signal payload | M1–M5 cards | BE-06 / FE-04 | PARTIAL |
| FR-011..013 | `fusion/*` | canonical result | decision banner | BE-07 / FE-04 | PARTIAL |
| FR-014/025 | audit/repositories | evidence/history | history/export | BE-08/09 / FE-07 | PARTIAL |
| FR-017/018 | evaluation | evaluation/status | evaluation | BE-14 / FE-08 | PARTIAL |
| FR-021..024 | DB/migrations (`0002_v3_jev_ai_audit.py`, `models.py`) | ready/status | status/admin | BE-02 (`test_be02_schema_migrations.py`, `test_migration_upgrade_downgrade.py`) | PASS |
| FR-026 / AI-001..010 | `jev_ai/*` | AI status/explain | advisory panel | BE-10..13 / FE-06 | SKELETON |
| FR-027/028 | Jev DB tables (`jev_ai_runs`, `jev_ai_feedback`) | AI runs/feedback | AI metadata/feedback | BE-02 / BE-13 / FE-06 | SCHEMA PASS |
| SEC-007 | schema/custody | N/A | N/A | BE-15 | SKELETON |
| SEC-008..010 | Jev guardrails | AI errors | advisory/error UX | BE-11/12/15 / FE-06/09 | SKELETON |
| FR-020 | `data/raw_pe.py` | analyze/file | gated upload | BE-19 | GATED |
