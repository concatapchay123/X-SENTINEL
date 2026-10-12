# 24 — BASELINE READINESS REPORT — V3

## Overall

**PLAN BE-01 (REPOSITORY, ENVIRONMENT & CONFIGURATION) PASS.**  
**PLAN BE-02 (MICROSOFT SQL SERVER V3 SCHEMA & MIGRATION) PASS.**  
**PLAN BE-03 (FASTAPI FOUNDATION, HEALTH & READINESS) PASS.**  
**PLAN BE-04 (DOMAIN, INPUT SCHEMA & SEMANTIC VIEWS) PASS.**  
**PLAN BE-05 (LIGHTGBM & SHAP MODEL SERVICE) PASS.**  
**READY FOR M1–M5 DETECTOR CORE (BE-06).**  
**NOT YET SCIENTIFICALLY ACCEPTED.**

| Area | Status | Start blocker? | Final acceptance blocker? |
|---|---|---:|---:|
| Repository / Environment / Config (BE-01) | COMPLETE PASS | No | No |
| Microsoft SQL Server / Migrations (BE-02) | COMPLETE PASS | No | backup/load/RBAC evidence |
| Backend Foundation / Readiness (BE-03) | COMPLETE PASS | No | No |
| Requirements | COMPLETE V3 | No | No |
| Architecture | COMPLETE V3 | No | actual integration evidence |
| Detection core | PARTIAL inherited skeleton | No | scientific configs + E0–E5 evidence |
| Backend API | PARTIAL | No | contract/integration tests |
| Frontend | PARTIAL runnable Streamlit | No | E2E/UX evidence |
| Jev AI spec | COMPLETE baseline | No | real model ID + integration/evaluation evidence |
| Jev AI runtime | SKELETON | No | endpoint/model tests if feature enabled |
| Security | PARTIAL | No local | auth, secrets, retention, threat tests |
| Deployment | PARTIAL | No | staging/rollback/load evidence |

## BE-01 Milestone Verification

- Repository layout: frozen and audit-passing (20 core files, 20 BE plans, 10 FE plans, 24 legacy plans).
- Dataset policy: `.gitignore` and `.dockerignore` enforce dataset exclusion; `datasets/.gitkeep` preserved; local working copy datasets (`bodmas`, `ember2018`) preserved intact without deletion.
- Environment & configuration: `.env.example`, `configs/jev_ai.yaml`, and `x_sentinel.config.Settings` synchronized and validated.
- Automated tests: 23 passed, 2 skipped (live DB integration).

## BE-02 Milestone Verification

- Canonical migration head: `0002_v3_jev_ai_audit` frozen and verified across Alembic, SQLAlchemy models, and `schema.sql`.
- V3 Jev AI audit schema: `jev_ai_runs` and `jev_ai_feedback` implemented with audit metadata, check constraints (`mode`, `status`, `rating`, `label`), indexes, and foreign keys (`analysis_job_id` ON DELETE SET NULL to preserve audit trail, `jev_ai_run_id` ON DELETE CASCADE).
- Scientific isolation & authority: zero detector fields in Jev tables; zero Jev fields in detector tables; simulated Jev failure does not corrupt or roll back canonical analysis results; blind evaluation ground truth strictly forbidden and absent from schema.
- Upgrade / downgrade verification: verified via offline SQL generation (`0001:0002` and `0002:0001`) and full live database migration cycle on an isolated scratch database (`xsentinel_migration_cycle_test`).
- Schema drift verification: `scripts/check_schema_drift.py` confirmed 0 differences between Alembic, SQLAlchemy `Base.metadata`, and live SQL Server database.
- Automated tests: 40 passed across all test suites with live database.

## BE-03 Milestone Verification

- FastAPI foundation: FastAPI application bootstrapped, mounts CORS middleware, error handlers, and canonical routes (`/health`, `/ready`, `/v1/config/status`, `/v1/ai/status`, `/v1/analyze/vector`).
- Health endpoint: `GET /health` verified responding with liveness metadata (`status: "ok"`), independent of database connectivity or Jev AI / LM Studio availability.
- Database revision readiness: `database_health` in `x_sentinel.database.health` inspects connectivity and Alembic `alembic_version` state; accurately distinguishes `current`, `behind`, `ahead`, `unmigrated`, `unknown`, and `unavailable`. `GET /ready` returns 503 on database unavailability or migration revision mismatch in a read-only manner without executing schema mutations.
- Jev AI status isolation: When disabled (`XS_JEV_AI_ENABLED=false`), zero network calls are made to LM Studio; `GET /v1/ai/status` returns `status: "disabled"`; Jev status never blocks detector readiness. When enabled, probes local endpoint with safe timeout, reports `available`, `unavailable`, or `misconfigured` without blocking detector readiness.
- Security: Zero database credentials, passwords, raw connection strings, or stack traces exposed in `/health`, `/ready`, `/v1/config/status`, or `/v1/ai/status`.
- Automated tests: 22 targeted tests in `test_be03_foundation_health_readiness.py`, 60 passed across full test suite (2 skipped for unconfigured live DB).

## BE-04 Milestone Verification

- Canonical vector schema: exactly 2,381 features enforced; ordering preserved; strict finite numeric bounds; booleans, strings, bytes, None, and nested shapes rejected; batch validation and named feature dictionary reconstruction implemented.
- Semantic views: Structural (255), Behavioral (1280), Metadata (846) view extraction verified; supports SliceSpec and IndicesSpec; mathematical bounds and disjoint/completeness integrity verified.
- View mapping hash identity: deterministic SHA-256 fingerprint (`276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb`) verified against `configs/views.demo.yaml`; index mutation and tampering detection verified.
- Scientific isolation & fail-closed security: unfreezed scientific mapping in `configs/views.scientific.yaml` safely fails closed (raises RuntimeError) when scientific mode is requested while OQ-01 remains pending freeze.
- Automated tests: 49 targeted tests in `test_be04_domain_schema_views.py`, 53 tests in data test suite (97% active statement coverage), 130 passed across full test suite (2 skipped for unconfigured live DB).
 
## BE-05 Milestone Verification

- Versioned model loading: LightGBM model loading with dimension validation (2,381 features), tree verification (1,000 trees), format validation, and in-memory caching to eliminate redundant 127MB reloads implemented.
- Model identity & artifact integrity: deterministic SHA-256 calculation (`509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2`), mismatch detection, missing/corrupted artifact detection, and structured `ModelMetadata` provenance verified.
- LightGBM inference service: single-sample and batch inference verified; input schema validation enforced via BE-04; output bounds ($P \in [0, 1]$), raw log-odds, and strict determinism verified; zero decision thresholds baked in.
- Local TreeSHAP explainability: exact local TreeSHAP attributions (2,381 features) and constant ensemble base values computed natively via LightGBM C++ TreeSHAP; mathematical additivity ($\sum \text{SHAP} + \text{base} = \text{margin}$) verified to tolerance $10^{-5}$; sequence protocol and batch explanations verified.
- Scientific isolation & fail-closed security: unfreezed scientific config in `configs/model.scientific.yaml` safely fails closed (raises `ModelConfigUnresolvedError`) while OQ-02 is pending; demo adapter disallowed when `allow_demo=False`; zero unauthorized fallback to demo on scientific failure.
- Automated tests: 30 targeted tests in `test_be05_lightgbm_shap_service.py`, 157 passed across full repo suite (5 skipped/deselected for unconfigured live DB).

## P0 scientific decisions

1. M4 exact canonical formula/normalization.
2. Fusion/calibration protocol.
3. Scientific LightGBM model identity/config.
4. Authoritative view mapping indices.

## P0 Jev AI integration decisions before enabling in accepted environment

1. Exact LM Studio model ID and model file provenance/license.
2. Context size/resource limits based on actual hardware.
3. Prompt/response retention policy.
4. RBAC roles allowed to invoke AI and read AI outputs.
5. Evaluation set for hallucination/grounding/usefulness.

These do not block detector implementation because Jev AI is optional.
