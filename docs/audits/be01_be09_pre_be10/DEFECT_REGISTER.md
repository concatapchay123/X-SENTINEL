# X-SENTINEL V3 — DEFECT REGISTER (BE-01 → BE-09)
## Comprehensive Technical Audit, Defect Tracking & Remediation

**Audit Scope**: PLAN-BE-01 Through PLAN-BE-09  
**Auditor**: Independent Technical Quality Assurance Team  
**Date**: October 12, 2026  
**Status**: ALL DEFECTS REPAIRED & VERIFIED PASS  

---

## 1. Defect Summary Matrix

| Defect ID | Severity | Affected Plan | Affected Component | File & Lines | Root Cause | Fix Applied | Verification Status |
|---|---|---|---|---|---|---|---|
| **D-01** | P1 (High) | BE-06 | `DetectorPipeline` | `backend/src/x_sentinel/detection/pipeline.py` (L100-104) | Hardcoded `.start:.stop` slice indexing on `target_view_map` instead of polymorphic `.split()`. Crashed on `IndicesSpec`. | Replaced slice access with `target_view_map.split(shap)`. | **VERIFIED PASS** (`test_pipeline_with_indices_spec_view_map_regression`) |
| **D-02** | P1 (High) | BE-06 / BE-09 | `AnalysisService` | `backend/src/x_sentinel/services/analysis_service.py` (L49-53) | Hardcoded `.start:.stop` slice indexing on `self.view_map` for SHAP vector. Crashed on `IndicesSpec`. | Replaced slice indexing with `self.view_map.split(shap)`. | **VERIFIED PASS** (`test_analysis_service_with_indices_spec_regression`) |
| **D-03** | P2 (Medium) | BE-06 | `M3ViewDetector` | `backend/src/x_sentinel/detection/m3_view.py` (L107-113) | `_prepare_views` fallback accessed `.start:.stop` when `view_map` lacked `.split()`. Crashed on non-slice specs. | Added polymorphic `_extract_view` calling `.extract()` if available. | **VERIFIED PASS** (`test_m3_view_contribution_and_concentration.py`) |
| **D-04** | P1 (High) | BE-05 / BE-06 | `M2StripDetector` & Model Services | `backend/src/x_sentinel/detection/m2_strip.py` (L86-89), `demo.py`, `lightgbm_service.py` | `M2StripDetector` called `float(pred_raw)`. Real model services returned `ModelInferenceResult`, raising `TypeError`. Real `infer()` also executed 16 redundant TreeSHAP calls. | Added `__float__` to `ModelInferenceResult`, added `predict_proba()` to `LightGBMService` and `DemoModelService`, updated `_get_model_fn` to prioritize `predict_proba`. | **VERIFIED PASS** (`test_detector_with_real_demo_model_service_regression`, `test_detector_with_real_lightgbm_service_regression`) |
| **D-05** | P2 (Medium) | BE-06 | `M4CrossViewDetector` | `backend/src/x_sentinel/detection/m4_cross_view.py` (L96-101) | `_extract_3_views` checked `isinstance(view_scores, (list, tuple))`, rejecting `np.ndarray` input of length 3 with `TypeError`. | Generalized sequence check to accept any sequence/array with `__len__ == 3` and `__iter__`. | **VERIFIED PASS** (`test_detector_supports_numpy_array_regression`) |
| **D-06** | P3 (Low) | BE-06 | `DetectorConfig` Loader | `backend/src/x_sentinel/detection/config.py` (L137-205) | `m_data.get("enabled", True)` returned `None` when YAML explicitly contained `null`, causing `bool(None) == False`. | Implemented `_parse_bool` helper with safe defaults and string parsing. | **VERIFIED PASS** (`test_load_config_with_explicit_null_and_string_booleans`) |
| **D-07** | P2 (Medium) | BE-02 / Integration | SQL Server Integration Tests | `tests/integration/test_database_roundtrip.py`, `tests/integration/test_migration_revision.py` | Tests checked only `os.getenv("XS_DATABASE_URL")`, skipping execution when environment variable was not explicitly set in the shell session even though Microsoft SQL Server was running locally on default connection. Also lacked post-test cleanup of inserted rows. | Added fallback to `settings.database_url` via connectability probe, and added explicit `DELETE` cleanup in `finally` block. | **VERIFIED PASS** (Both tests now execute and pass: 424/424 total suite passed with 0 skipped) |

---

## 2. Detailed Defect Reports & Remediation

### D-01: DetectorPipeline View Slicing AttributeError
- **Symptom**: Calling `DetectorPipeline.evaluate()` or `DetectorPipeline.scores()` with an `IndicesSpec`-based `ViewMap` raised `AttributeError: 'IndicesSpec' object has no attribute 'start'`.
- **Root Cause**: Assumed `target_view_map.structural`, `behavioral`, and `metadata` were instances of `SliceSpec`, violating the `ViewSpec = SliceSpec | IndicesSpec` polymorphic union contract established in BE-04.
- **Remediation**: Replaced slice dictionary construction with polymorphic `target_view_map.split(shap)` which delegates to `.extract()`.
- **Regression Verification**: `test_pipeline_with_indices_spec_view_map_regression` PASS.

### D-02: AnalysisService View Slicing AttributeError
- **Symptom**: Calling `AnalysisService.analyze_vector()` with an `IndicesSpec` view map crashed with `AttributeError`.
- **Root Cause**: Sliced SHAP values via `[self.view_map.structural.start : self.view_map.structural.stop]`.
- **Remediation**: Replaced manual slice indexing with polymorphic `self.view_map.split(shap)`.
- **Regression Verification**: `test_analysis_service_with_indices_spec_regression` PASS.

### D-03: M3ViewDetector Fallback Slice Access
- **Symptom**: When `view_map` had attributes `structural`, `behavioral`, `metadata` but lacked `.split()`, `_prepare_views` directly read `.start` and `.stop`.
- **Root Cause**: Missing check for `.extract()` on individual view specifications.
- **Remediation**: Implemented `_extract_view(spec)` helper checking `hasattr(spec, "extract")` before falling back to `.start:.stop`.
- **Regression Verification**: `test_m3_view_contribution_and_concentration.py` PASS.

### D-04: M2 Tabular STRIP TypeError & Redundant TreeSHAP Overhead
- **Symptom**: `M2StripDetector.detect(x, model_service=service)` raised `TypeError: float() argument must be a string or a real number, not 'ModelInferenceResult'` when passing real model services. Additionally, computing 16 TreeSHAP explanations per detection took $>15$s.
- **Root Cause**: Tabular STRIP only requires probability $P(y=1|x)$, not attributions, but called `infer()` which computed full TreeSHAP, and did not handle `ModelInferenceResult`.
- **Remediation**: Implemented `__float__` on `ModelInferenceResult`, added fast `predict_proba(vector)` to `LightGBMService` and `DemoModelService`, and updated `_get_model_fn` to prioritize `predict_proba`.
- **Regression Verification**: `test_detector_with_real_demo_model_service_regression`, `test_detector_with_real_lightgbm_service_regression` PASS.

### D-05: M4 Cross-View Detector Rejection of NumPy Arrays
- **Symptom**: Passing a 3-element `numpy.ndarray` to `M4CrossViewDetector.detect()` raised `TypeError: Invalid view_scores type: <class 'numpy.ndarray'>`.
- **Root Cause**: `_extract_3_views` used `isinstance(view_scores, (list, tuple))`.
- **Remediation**: Generalized sequence check to accept any sequence/array with `__len__ == 3` and `__iter__`.
- **Regression Verification**: `test_detector_supports_numpy_array_regression` PASS.

### D-06: Detector Config Parser Boolean Parsing Null Defect
- **Symptom**: When YAML explicitly contained `null` (`enabled: null`), `m_data.get("enabled", True)` returned `None`, which `bool(None)` evaluated to `False` instead of honoring the default.
- **Root Cause**: Unsafe dict get pattern combined with standard Python `bool(None) == False`.
- **Remediation**: Implemented `_parse_bool(val, default)` helper handling `None`, booleans, and string representations.
- **Regression Verification**: `test_load_config_with_explicit_null_and_string_booleans` PASS.

### D-07: SQL Server Integration Test Skips & Missing Row Cleanup
- **Symptom**: Running `pytest` in standard environment skipped `test_database_roundtrip.py` and `test_migration_revision.py` because `os.getenv("XS_DATABASE_URL")` was not explicitly set in the shell session, despite live Microsoft SQL Server running on `settings.database_url`. Furthermore, `test_database_is_migrated_and_accepts_job` left orphan test rows in the database.
- **Root Cause**: Over-reliance on raw `os.environ` check without checking `settings.database_url` fallback, and missing `finally` cleanup block.
- **Remediation**: Updated both tests to inspect `os.getenv("XS_DATABASE_URL", settings.database_url)` with live connectivity verification, and added explicit `DELETE` in `finally` block.
- **Regression Verification**: Full pytest suite executed: 424 passed, 0 skipped, 0 failed.
