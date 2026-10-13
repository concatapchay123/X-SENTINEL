# 18 — FEATURE MATRIX — V3

Statuses: Not Started → Skeleton → Partial → Implemented → Integrated → Tested → Verified → Accepted.

| Feature | Current V3 status | Exit evidence |
|---|---|---|
| Vector schema | Tested / Verified | UT/API invalid/boundary (`test_be04_domain_schema_views.py`) |
| 3-view mapping | Tested / Verified (Demo locked; Scientific gated) | authoritative demo map hash (`276be235...`) + tests |
| LightGBM/SHAP | Skeleton/Demo | real model identity + deterministic evidence |
| M1–M5 | Skeleton; M4 freeze pending | unit/golden + experiments |
| Fusion/D1 | Tested / Verified | frozen weighted_sum, D1 empirical quantile calibration, Wilson 95% CI, golden cases (BE-07) |
| Microsoft SQL Server | V3 schema/migration defined | live migration/drift/backup/load evidence |
| Audit & Evidence | Tested / Verified | Canonical evidence schema, SHA-256 integrity, write failure rollback, repositories (`test_be08_*`) |
| Core API | Tested / Verified | Canonical Analysis/History/Alerts/Evidence contracts, OpenAPI 3.1.0 contract tests, Role-based auth (`test_be09_*`) |
| Streamlit frontend | Skeleton | E2E exact rendering |
| Jev AI client/guardrails | Tested / Verified | local-only client, strict allowlist/redaction/injection guardrails, orchestrator workflows (`test_be10_*`, `test_be11_*`, `test_be12_*`) |
| Jev AI persistence/API | Tested / Verified / Accepted | Non-blocking persistence, `/v1/ai/explain`, `/v1/ai/runs`, `/v1/ai/runs/{run_id}/feedback`, RBAC/IDOR, live SQL Server & transaction isolation tests (`test_be13_jev_persistence_api_feedback.py`) |
| Jev AI frontend | Planned | FE-06 E2E/advisory separation |
| E0–E5 | Tested / Verified (Frozen Candidate Run; Strict Scientific Freeze Gated) | `artifacts/evaluation/be14_candidate_suite/`, `verify_run_artifacts`, `recompute_metrics_from_raw`, `test_be14_threat_simulation_e0_e5_statistics.py` |
| Blind evaluation | Tested / Verified | 3-role `BlindCustodyGuard`, SHA-256 `BlindPredictionPackage`, `BlindEvaluator` (`test_be14_threat_simulation_e0_e5_statistics.py`) |
| Docker/CI | Skeleton | clean build/migration/test evidence |
| Raw PE/LIEF | Phase 2 | equivalence + safety tests |
