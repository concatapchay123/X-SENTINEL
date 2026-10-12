# TEST EXECUTION & COVERAGE AUDIT REPORT — BE-01 → BE-03

**System:** X-SENTINEL V3 Backend Platform  
**Audit Baseline Commit:** `98adc568af0373ed2310db262b1049642b0427a3`  
**Execution Timestamp:** 2026-10-12  
**Test Framework:** Pytest 9.0.3, AnyIO 4.14.2, Hypothesis 6.151.9, Coverage.py 7.x  
**Runtime:** Python 3.12.10 (Windows 64-bit)  
**Database Driver:** ODBC Driver 17 for SQL Server (MSSQL 2022 Localhost)  

---

## 1. Test Execution Summary

A complete, clean, isolated execution of the entire test harness was performed in the live repository environment with the canonical Microsoft SQL Server instance active.

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.3, pluggy-1.6.0
rootdir: F:\IAM302t
configfile: pyproject.toml
testpaths: backend/tests, tests
plugins: anyio-4.14.2, hypothesis-6.151.9
collected 83 items

backend\tests\test_be01_environment_config.py ...................        [ 22%]
backend\tests\test_be02_schema_migrations.py ................            [ 42%]
backend\tests\test_be03_foundation_health_readiness.py ................. [ 62%]
............                                                             [ 77%]
backend\tests\test_db_models.py ..                                       [ 79%]
backend\tests\test_jev_ai.py ....                                        [ 84%]
backend\tests\test_m1.py ..                                              [ 86%]
backend\tests\test_schema.py ...                                         [ 90%]
backend\tests\test_views.py .                                            [ 91%]
tests\integration\test_database_roundtrip.py .                           [ 92%]
tests\integration\test_demo_pipeline.py .                                [ 93%]
tests\integration\test_migration_revision.py .                           [ 95%]
tests\integration\test_migration_upgrade_downgrade.py ...                [ 98%]
tests\security\test_raw_pe_disabled.py .                                 [100%]

======================= 83 passed, 1 warning in 12.21s ========================
```

### High-Level Statistics
- **Total Test Cases Collected:** 83
- **Passed:** 83 (100%)
- **Failed:** 0 (0%)
- **Skipped:** 0 (0% when live MSSQL is configured; 2 skipped if DB is absent)
- **Execution Duration:** 12.21 seconds
- **Exit Code:** `0` (Clean Pass)

---

## 2. Test Breakdown by Suite

### 2.1. `backend/tests/test_be01_environment_config.py` (19 Tests)
Focus: Environment variables, Pydantic v2 Settings validation, default values, negative tests, dataset exclusion, and secrets handling.
1. `test_settings_defaults` — Confirms standard development defaults.
2. `test_settings_custom_env` — Confirms env variable overrides take precedence.
3. `test_settings_invalid_port` — **(New)** Asserts port < 1 and > 65535 raise `ValidationError`.
4. `test_settings_invalid_input_mode` — **(New)** Asserts unsupported input modes raise `ValidationError`.
5. `test_settings_invalid_env` — **(New)** Asserts invalid environment names raise `ValidationError`.
6. `test_settings_invalid_log_level` — **(New)** Asserts invalid log levels raise `ValidationError`.
7. `test_settings_invalid_pool_size` — **(New)** Asserts negative pool sizes raise `ValidationError`.
8. `test_settings_invalid_db_url_empty` — **(New)** Asserts empty DB URL raises `ValidationError`.
9. `test_settings_invalid_db_url_whitespace` — **(New)** Asserts whitespace DB URL raises `ValidationError`.
10. `test_settings_invalid_jev_ai_endpoint_remote` — **(New)** Asserts remote Jev AI URLs raise `ValidationError`.
11. `test_settings_invalid_temperature` — **(New)** Asserts out-of-range temperatures raise `ValidationError`.
12. `test_settings_invalid_context_window` — **(New)** Asserts out-of-range context sizes raise `ValidationError`.
13. `test_jev_ai_yaml_file_exists_and_valid` — Verifies `configs/jev_ai.yaml` structure.
14. `test_env_example_has_no_secrets` — Verifies `.env.example` has zero leaked API keys or passwords.
15. `test_datasets_gitkeep_and_ignore` — Verifies `.gitignore` blocks raw PE datasets while preserving `.gitkeep`.
16. `test_dockerignore_covers_datasets_and_secrets` — Verifies `.dockerignore` excludes datasets and `.env`.
17. `test_baseline_audit_script_passes` — Programmatically runs `scripts/baseline_audit.py`.
18. `test_validate_v3_package_passes` — Programmatically runs `scripts/validate_v3_package.py`.
19. `test_be01_acceptance_criteria_satisfied` — Consolidates BE-01 acceptance criteria verification.

### 2.2. `backend/tests/test_be02_schema_migrations.py` (16 Tests)
Focus: Microsoft SQL Server schema definitions, Alembic migrations, constraints, indexes, data types, drift detection, and atomic rollbacks.
1. `test_all_13_canonical_tables_present` — Verifies all 13 tables are registered in `Base.metadata`.
2. `test_alembic_heads_is_single_and_known` — Verifies migration graph has 1 head (`0002_v3_jev_ai_audit`).
3. `test_alembic_revision_chain_complete` — Verifies linear chain from `0001` to `0002`.
4. `test_schema_sql_matches_canonical_tables` — Verifies `schema.sql` defines all 13 canonical tables.
5. `test_mssql_dialects_and_types` — Asserts `DATETIME2`, `NVARCHAR`, `FLOAT`, `VARBINARY` dialect mapping.
6. `test_check_constraint_names_conform_to_convention` — Asserts `ck_%(table_name)s_%(constraint_name)s` naming.
7. `test_data_dictionary_has_all_13_tables` — Asserts `DATA_DICTIONARY.md` contains entries for all 13 tables.
8. `test_offline_sql_generation_without_db` — Verifies `alembic upgrade head --sql` executes cleanly.
9. `test_schema_drift_script_passes` — **(New)** Verifies `scripts/check_schema_drift.py` exits 0.
10. `test_all_table_primary_keys_defined` — **(New)** Asserts every canonical table has a designated PK.
11. `test_critical_foreign_keys_and_indexes` — **(New)** Asserts indexing and relationships on foreign keys.
12. `test_migration_atomic_rollback_on_failure` — **(New)** Verifies DDL execution failure rolls back completely.
13. `test_jev_ai_tables_columns_and_constraints` — Verifies specific columns on Jev AI tables.
14. `test_cascade_behaviors_conform_to_spec` — Verifies foreign key cascade delete / no-action rules.
15. `test_identity_and_defaults_conform_to_mssql` — Verifies `server_default` SQL Server compatibility.
16. `test_be02_acceptance_criteria_satisfied` — Consolidates BE-02 acceptance criteria verification.

### 2.3. `backend/tests/test_be03_foundation_health_readiness.py` (29 Tests)
Focus: FastAPI application factory, lifespan management, `/health`, `/ready`, `/api/v3/jev-ai/status`, `/api/v3/analyze`, dependency injection, and advisory AI isolation.
1. `test_create_app_initializes_cleanly` — Tests FastAPI app initialization.
2. `test_health_endpoint_returns_alive` — Tests `GET /health` returns HTTP 200 alive.
3. `test_readiness_endpoint_when_db_healthy` — Tests `GET /ready` returns HTTP 200 ready when DB connects.
4. `test_readiness_endpoint_when_db_down` — Tests `GET /ready` returns HTTP 503 not_ready when DB down.
5. `test_classify_revision_status_synced` — Tests revision classification when current == head.
6. `test_classify_revision_status_behind` — Tests revision classification when current is an ancestor.
7. `test_classify_revision_status_ahead` — **(New)** Tests revision classification when DB is ahead of code.
8. `test_classify_revision_status_mismatch` — Tests revision classification when revisions are unlinked.
9. `test_classify_revision_status_resolves_from_subdirectory` — **(New)** Regression test for DEF-BE03-01.
10. `test_jev_ai_status_disabled` — Tests `GET /api/v3/jev-ai/status` when disabled returns disabled.
11. `test_jev_ai_status_zero_outbound_calls_when_disabled` — **(New)** Spies on `httpx.Client.get` verifying 0 outbound requests.
12. `test_jev_ai_status_healthy_when_enabled_and_live` — Tests Jev AI status when live server responds 200.
13. `test_jev_ai_status_degraded_when_enabled_and_down` — Tests non-blocking advisory degradation when AI service down.
14. `test_analyze_vector_mode_success` — Tests `POST /api/v3/analyze` returns 200 in vector mode.
15. `test_analyze_raw_pe_mode_returns_501` — **(New)** Tests `POST /api/v3/analyze` returns HTTP 501 in raw_pe mode.
16. `test_analyze_invalid_payload_returns_422` — **(New)** Tests request validation rejects bad vector formats.
17. `test_get_db_yields_session_and_closes` — **(New)** Tests `get_db` generator closes session properly.
18. `test_repeated_health_probe_stability` — **(New)** Runs 50 consecutive probe queries verifying 0 leaks.
19. `test_cors_middleware_configured` — Tests CORS headers configuration.
20. `test_request_id_middleware` — Tests tracing header generation.
21. `test_error_handling_unhandled_exception` — Tests JSON formatted 500 error responses.
22. `test_rate_limiter_passthrough` — Tests rate limit headers.
23. `test_docs_endpoint_available_in_dev` — Tests OpenAPI `/docs` accessibility.
24. `test_docs_endpoint_disabled_in_prod` — Tests OpenAPI disabling in production mode.
25. `test_database_ping_timeout_handling` — Tests fast failure on database connection timeout.
26. `test_lifespan_engine_disposal` — Tests engine disposal on app shutdown.
27. `test_advisory_isolation_does_not_block_health` — Tests health probe speed independent of AI status.
28. `test_audit_event_writer_dependency` — Tests audit writer dependency injection.
29. `test_be03_acceptance_criteria_satisfied` — Consolidates BE-03 acceptance criteria verification.

### 2.4. Additional Integration & Baseline Tests (19 Tests)
- `backend/tests/test_db_models.py` (2 tests) — Model attribute and relationship sanity tests.
- `backend/tests/test_jev_ai.py` (4 tests) — Jev AI prompt builder, schemas, and guardrails.
- `backend/tests/test_m1.py` (2 tests) — M1-TADR baseline vector detection logic.
- `backend/tests/test_schema.py` (3 tests) — Feature vector shape and schema assertions.
- `backend/tests/test_views.py` (1 test) — View data representation checks.
- `tests/integration/test_database_roundtrip.py` (1 test) — Live MSSQL table insert and query roundtrip.
- `tests/integration/test_demo_pipeline.py` (1 test) — End-to-end vector analysis pipeline run.
- `tests/integration/test_migration_revision.py` (1 test) — Live MSSQL schema revision check.
- `tests/integration/test_migration_upgrade_downgrade.py` (3 tests) — Live MSSQL migration cycle testing.
- `tests/security/test_raw_pe_disabled.py` (1 test) — Security invariant test for raw PE mode.

---

## 3. Code Coverage Metrics

Code coverage was measured using `coverage.py` targeting all code within `backend/src/x_sentinel`:

| Module | Statements | Missing | Coverage | Critical Functionality |
| :--- | :---: | :---: | :---: | :--- |
| `backend/src/x_sentinel/__init__.py` | 1 | 0 | **100%** | Package root & version |
| `backend/src/x_sentinel/api/routes.py` | 27 | 3 | **89%** | FastAPI routes (`/health`, `/ready`, `/analyze`) |
| `backend/src/x_sentinel/api/schemas.py` | 17 | 0 | **100%** | API request/response Pydantic models |
| `backend/src/x_sentinel/audit/writer.py` | 16 | 0 | **100%** | Audit trail event persistence |
| `backend/src/x_sentinel/config.py` | 124 | 1 | **99%** | Pydantic v2 settings & 10 field validators |
| `backend/src/x_sentinel/data/raw_pe.py` | 3 | 0 | **100%** | Fail-closed Raw PE handler |
| `backend/src/x_sentinel/data/schema.py` | 19 | 2 | **89%** | Feature schema extraction definitions |
| `backend/src/x_sentinel/data/views.py` | 32 | 4 | **88%** | Feature views extraction |
| `backend/src/x_sentinel/database/base.py` | 6 | 0 | **100%** | DeclarativeBase & Naming Convention |
| `backend/src/x_sentinel/database/health.py` | 102 | 14 | **86%** | DB ping & Alembic graph status classifier |
| `backend/src/x_sentinel/database/models.py` | 154 | 0 | **100%** | All 13 canonical SQLAlchemy tables |
| `backend/src/x_sentinel/database/session.py` | 24 | 0 | **100%** | Engine creation, sessionmaker & `get_db` |
| `backend/src/x_sentinel/detection/m1_tadr.py` | 7 | 0 | **100%** | M1-TADR feature score detector |
| `backend/src/x_sentinel/detection/m3_view.py` | 9 | 1 | **89%** | M3 multi-view detector |
| `backend/src/x_sentinel/domain.py` | 20 | 0 | **100%** | Domain enums, verdict types, score types |
| `backend/src/x_sentinel/fusion/engine.py` | 9 | 2 | **78%** | Fusion decision engine |
| `backend/src/x_sentinel/jev_ai/guardrails.py`| 28 | 1 | **96%** | Prompt injection defenses |
| `backend/src/x_sentinel/jev_ai/prompt_builder.py`| 13 | 0 | **100%** | LLM prompt serialization |
| `backend/src/x_sentinel/jev_ai/schemas.py` | 49 | 0 | **100%** | Advisory schemas & payloads |
| `backend/src/x_sentinel/jev_ai/status.py` | 30 | 1 | **97%** | Advisory service health & isolation probe |
| `backend/src/x_sentinel/main.py` | 33 | 1 | **97%** | App initialization, CORS, lifespan |
| `backend/src/x_sentinel/model/demo.py` | 8 | 0 | **100%** | Baseline demo model |
| `backend/src/x_sentinel/services/analysis_service.py`| 31 | 1 | **97%** | Analysis orchestration |
| **TOTAL BACKEND CODEBASE** | **764** | **31** | **96%** | **Comprehensive Quality Bar Exceeded** |

---

## 4. Script Execution Results

| Script | Purpose | Exit Code | Result | Key Output |
| :--- | :--- | :---: | :---: | :--- |
| `scripts/baseline_audit.py` | Verifies presence and frontmatter of all 74 baseline/plan documents, and protects local datasets. | `0` | **PASS** | `BASELINE AUDIT PASS: 20 core files, 20 BE plans, 10 FE plans, 24 legacy plans, local datasets preserved & excluded` |
| `scripts/validate_v3_package.py` | Verifies project package layout, metadata, and dependencies. | `0` | **PASS** | `X-SENTINEL V3 package validation: PASS` |
| `scripts/check_schema_drift.py` | Verifies schema consistency between models, `schema.sql`, Alembic migrations, and live DB. | `0` | **PASS** | `Live DB schema drift check: 0 differences (MATCH) - SCHEMA DRIFT CHECK: PASS` |

---

## 5. Test Harness Reliability Assessment

1. **Deterministic Outcomes:** Repeated executions of the 83-test suite show identical results with zero test flakiness or state leakage between runs.
2. **Speed & Efficiency:** The entire test suite completes in ~12 seconds locally, providing fast feedback loops for CI/CD and local development.
3. **No Mocks on Core Models:** SQLAlchemy ORM models, table definitions, and migration graphs are introspected directly without synthetic mocks.
