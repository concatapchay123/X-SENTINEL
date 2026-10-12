# DEFECT REGISTER & REMEDIATION LOG — BE-01 → BE-03

**System:** X-SENTINEL V3 Backend Platform  
**Audit Baseline Commit:** `98adc568af0373ed2310db262b1049642b0427a3`  
**Date:** 2026-10-12  
**Auditor:** Principal Backend & System Reliability Auditor  

---

## 1. Summary of Identified Defects

During the rigorous audit of phases BE-01, BE-02, and BE-03, four (4) distinct defects were uncovered across configuration validation, database drift detection, health check revision traversal, and test harness metadata. All four defects were addressed, code fixes committed to the working tree, and regression tests added.

| Defect ID | Plan | Title / Nature | Severity | Target File | Status |
| :--- | :--- | :--- | :---: | :--- | :---: |
| **DEF-BE01-01** | BE-01 | Missing Fail-Fast Field Validation in Pydantic Settings | **P1 (High)** | `backend/src/x_sentinel/config.py` | **CLOSED (VERIFIED)** |
| **DEF-BE02-01** | BE-02 | Incomplete Scope in `check_schema_drift.py` (Missed 11 Tables) | **P2 (Medium)** | `scripts/check_schema_drift.py` | **CLOSED (VERIFIED)** |
| **DEF-BE03-01** | BE-03 | Alembic CWD Resolution & Graph Traversal Failure in Health Checks | **P0 (Critical)** | `backend/src/x_sentinel/database/health.py` | **CLOSED (VERIFIED)** |
| **DEF-BE03-02** | BE-03 | Misleading Pytest Database Marker Description | **P3 (Low)** | `pyproject.toml` | **CLOSED (VERIFIED)** |

---

## 2. Detailed Defect Logs & Remediation Evidence

### DEF-BE01-01: Missing Fail-Fast Field Validation in Pydantic Settings

#### 1. Metadata
- **Defect ID:** DEF-BE01-01
- **Severity:** P1 (High)
- **Lifecycle Phase:** BE-01 (Configuration & Environment)
- **Target Component:** `backend/src/x_sentinel/config.py`
- **Class Affected:** `Settings` (Pydantic v2 `BaseSettings`)

#### 2. Root Cause Analysis
The original `Settings` class relied solely on primitive Pydantic type hints (`int`, `str`, `bool`, `float`). It lacked semantic domain validators for boundary conditions:
- `port`: Accepted negative values (e.g., `-1`) and values above 65535.
- `input_mode`: Accepted any arbitrary string (e.g., `"unsupported"`), delaying failure until a request hit the service.
- `database_url`: Accepted empty strings and whitespace strings without raising an error at startup.
- `database_pool_size`, `database_max_overflow`, `database_pool_timeout`: Accepted negative numbers.
- `jev_ai_endpoint`: Accepted arbitrary external URLs (e.g., `https://evil.corp/api`) even though the security baseline mandates that Jev AI advisory service must strictly run on localhost/127.0.0.1.

#### 3. Reproduction Steps
```python
from x_sentinel.config import Settings
# Prior to fix: this succeeded silently without error
bad_settings = Settings(port=-5, input_mode="invalid", database_pool_size=-10)
assert bad_settings.port == -5 # Silent pass!
```

#### 4. Remediation Applied
In `backend/src/x_sentinel/config.py`:
- Added `@field_validator("port")` enforcing `1 <= v <= 65535`.
- Added `@field_validator("input_mode")` enforcing membership in `{"vector", "raw_pe"}`.
- Added `@field_validator("database_url")` ensuring URL is non-empty and non-whitespace.
- Added `@field_validator("database_pool_size", "database_max_overflow", "database_pool_timeout", "circuit_breaker_max_failures", "circuit_breaker_reset_seconds")` ensuring values are `>= 0` (or `> 0` where required).
- Added `@field_validator("log_level")` ensuring valid uppercase standard logging levels.
- Added `@field_validator("jev_ai_temperature")` enforcing `0.0 <= v <= 2.0`.
- Added `@field_validator("jev_ai_context_window_tokens")` enforcing `100 <= v <= 200_000`.
- Added `@model_validator(mode="after")` enforcing that when `jev_ai_enabled=True`, the `jev_ai_endpoint` must resolve to `localhost` or `127.0.0.1`.

#### 5. Verification & Regression Tests
Added 10 negative validation test cases in `backend/tests/test_be01_environment_config.py`:
- `test_settings_invalid_port`
- `test_settings_invalid_input_mode`
- `test_settings_invalid_env`
- `test_settings_invalid_log_level`
- `test_settings_invalid_pool_size`
- `test_settings_invalid_db_url_empty`
- `test_settings_invalid_db_url_whitespace`
- `test_settings_invalid_jev_ai_endpoint_remote`
- `test_settings_invalid_temperature`
- `test_settings_invalid_context_window`
All 10 tests passed with `ValidationError` properly raised and validated.

---

### DEF-BE02-01: Incomplete Scope in `check_schema_drift.py`

#### 1. Metadata
- **Defect ID:** DEF-BE02-01
- **Severity:** P2 (Medium)
- **Lifecycle Phase:** BE-02 (MSSQL Schema & Migration)
- **Target Component:** `scripts/check_schema_drift.py`

#### 2. Root Cause Analysis
`scripts/check_schema_drift.py` is the official CI tool to detect divergence between SQLAlchemy models, `schema.sql`, and the live database. However, the initial dictionary `EXPECTED_TABLE_COLUMNS` contained definitions for only 2 tables:
- `jev_ai_audit_events`
- `jev_ai_collaboration_sessions`

The script completely omitted the 11 canonical malware detection, feature extraction, and pipeline tables: `threat_intel_iocs`, `dataset_samples`, `pipeline_runs`, `feature_extractions`, `models`, `fusion_weights`, `samples`, `predictions`, `fusion_decisions`, `audit_logs`, `adversarial_evaluations`. As a consequence, any schema drift, missing columns, or dropped constraints in the core detection pipeline would go unnoticed.

#### 3. Reproduction Steps
```bash
python scripts/check_schema_drift.py
# Prior to fix: only reported checking 2 tables, giving false confidence on the core schema
```

#### 4. Remediation Applied
In `scripts/check_schema_drift.py`:
- Populated `EXPECTED_TABLE_COLUMNS` with all 13 canonical tables and their 68 distinct columns.
- Updated `check_models()` to assert all 13 tables exist in `Base.metadata.tables`.
- Updated `check_schema_sql()` to ensure all 13 tables are present in `database/schema/schema.sql`.
- Updated `check_live_db()` to inspect all 13 tables via `sqlalchemy.inspect(engine)` and report missing tables or mismatched columns.

#### 5. Verification & Regression Tests
- Executed `python scripts/check_schema_drift.py` against live MSSQL scratch database. Output confirmed:
  `Live DB schema drift check: 0 differences (MATCH) - SCHEMA DRIFT CHECK: PASS`.
- Added automated test in `backend/tests/test_be02_schema_migrations.py::test_schema_drift_script_passes`. PASSED.

---

### DEF-BE03-01: Alembic CWD Resolution & Graph Traversal Failure in Health Checks

#### 1. Metadata
- **Defect ID:** DEF-BE03-01
- **Severity:** P0 (Critical)
- **Lifecycle Phase:** BE-03 (FastAPI Foundation & Health Probes)
- **Target Component:** `backend/src/x_sentinel/database/health.py`
- **Function Affected:** `classify_revision_status(current_rev, head_rev)`

#### 2. Root Cause Analysis
1. **Relative Path Resolution:** The function instantiated `Config("database/alembic.ini")`. When the service was invoked with CWD set to `backend/` or when tests were run from subfolders, `alembic.ini` could not be found, causing an unhandled exception inside the try block that fell back to returning `mismatch` instead of `behind` or `synced`.
2. **Non-Scalar Down-Revision Traversal:** When Alembic migration scripts branch or merge, `script.down_revision` can be a `tuple` of multiple parent revision strings (e.g., `("rev_a", "rev_b")`) or `None` at the root. The existing loop assumed `down_revision` was always a single string or `None`, which causes traversal breakage or crashes when navigating DAGs.

#### 3. Reproduction Steps
```python
import os
from x_sentinel.database.health import classify_revision_status

# Run from backend directory
os.chdir("backend")
status = classify_revision_status("0001_initial_schema", "0002_v3_jev_ai_audit")
# Prior to fix: returned "mismatch" because Config("database/alembic.ini") failed!
assert status == "behind" # FAILED with AssertionError
```

#### 4. Remediation Applied
In `backend/src/x_sentinel/database/health.py`:
- Dynamically resolved `alembic.ini` relative to the file location:
  `alembic_ini_path = Path(__file__).resolve().parents[4] / "database" / "alembic.ini"`
  with fallback to CWD if not found.
- Updated graph traversal to handle both scalar string and `tuple`/`list` representations of `down_revision`:
  ```python
  parent = script.down_revision
  if isinstance(parent, (tuple, list)):
      curr = parent[0] if parent else None
  else:
      curr = parent
  ```

#### 5. Verification & Regression Tests
Added regression tests in `backend/tests/test_be03_foundation_health_readiness.py`:
- `test_classify_revision_status_resolves_from_subdirectory`: Switches CWD to `backend/` and asserts `classify_revision_status("0001_initial_schema", "0002_v3_jev_ai_audit") == "behind"`. PASSED.
- `test_classify_revision_status_ahead`: Tests when current revision is ahead of head revision. PASSED.
- `test_classify_revision_status_mismatch`: Tests unlinked revisions. PASSED.

---

### DEF-BE03-02: Misleading Pytest Database Marker Description

#### 1. Metadata
- **Defect ID:** DEF-BE03-02
- **Severity:** P3 (Low)
- **Lifecycle Phase:** BE-03 (Testing & Configuration)
- **Target Component:** `pyproject.toml`

#### 2. Root Cause Analysis
The pytest marker configuration in `pyproject.toml` read:
```toml
[tool.pytest.ini_options]
markers = [
    "db: marks tests that require a live PostgreSQL database",
    ...
]
```
Per Architecture Decision Record ADR-007, Microsoft SQL Server is the sole approved operational database engine for X-SENTINEL V3. Having `PostgreSQL` documented created confusion and false assumptions in automated CI scripts.

#### 3. Reproduction Steps
Inspect `pyproject.toml` under `tool.pytest.ini_options.markers`.

#### 4. Remediation Applied
Updated `pyproject.toml`:
```toml
markers = [
    "db: marks tests that require a live Microsoft SQL Server database",
    "integration: integration tests across multiple components",
    "security: security and adversarial hardening tests",
]
```

#### 5. Verification & Regression Tests
Pytest executes without warnings regarding unrecognized markers; `pytest -m db` selectively runs live MSSQL tests. PASSED.

---

## 3. Defect Prevention & Lessons Learned

1. **Deterministic Path Resolution:** File paths for assets (migrations, configs, templates) must always anchor on `__file__` or `importlib.resources`, never trusting process CWD.
2. **Pydantic Type Boundary Defense:** Type hints are insufficient for production security; explicit validators must guard all port, URL, mode, and pool constraints.
3. **Comprehensive Drift Testing:** Validation scripts must mirror the complete data model, not a sample subset.
