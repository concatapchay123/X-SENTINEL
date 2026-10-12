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
| Core API | Skeleton | contract/integration tests |
| Streamlit frontend | Skeleton | E2E exact rendering |
| Jev AI client/guardrails | V3 skeleton | mocked + live local-model integration tests |
| Jev AI persistence/API | Planned/DB schema defined | BE-13 integration tests |
| Jev AI frontend | Planned | FE-06 E2E/advisory separation |
| E0–E5 | Runner skeleton | actual immutable outputs |
| Blind evaluation | Planned | custody/access logs + independent scorer |
| Docker/CI | Skeleton | clean build/migration/test evidence |
| Raw PE/LIEF | Phase 2 | equivalence + safety tests |
