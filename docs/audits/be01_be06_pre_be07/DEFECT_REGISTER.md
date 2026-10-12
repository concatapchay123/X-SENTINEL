# X-SENTINEL V3 — DEFECT REGISTER
## Technical Audit & Verification (PLAN-BE-01 to PLAN-BE-06)

**Audit Version**: 3.0.0-AUDIT  
**Date**: October 12, 2026  
**Status**: ALL DEFECTS REPAIRED & VERIFIED  

---

### Defect Summary Matrix

| Defect ID | Severity | Affected Component | File & Lines | Root Cause | Fix Applied | Verification Status |
|---|---|---|---|---|---|---|
| **D-01** | P1 (High) | `DetectorPipeline` | `backend/src/x_sentinel/detection/pipeline.py` (L100-104) | Hardcoded `.start:.stop` slice indexing on `target_view_map` instead of polymorphic `.split()`. Crashed on `IndicesSpec`. | Replaced slice access with `target_view_map.split(shap)`. | **VERIFIED PASS** (`test_pipeline_with_indices_spec_view_map_regression`) |
| **D-02** | P1 (High) | `AnalysisService` | `backend/src/x_sentinel/services/analysis_service.py` (L49-53) | Hardcoded `.start:.stop` slice indexing on `self.view_map` for SHAP vector. Crashed on `IndicesSpec`. | Replaced slice indexing with `self.view_map.split(shap)`. | **VERIFIED PASS** (`test_analysis_service_with_indices_spec_regression`) |
| **D-03** | P2 (Medium) | `M3ViewDetector` | `backend/src/x_sentinel/detection/m3_view.py` (L107-113) | `_prepare_views` fallback accessed `.start:.stop` when `view_map` lacked `.split()`. Crashed on non-slice specs. | Added polymorphic `_extract_view` calling `.extract()` if available. | **VERIFIED PASS** (`test_m3_view_contribution_and_concentration.py`) |
| **D-04** | P1 (High) | `M2StripDetector` & Model Services | `backend/src/x_sentinel/detection/m2_strip.py` (L86-89), `demo.py`, `lightgbm_service.py` | `M2StripDetector` called `float(pred_raw)`. Real model services returned `ModelInferenceResult`, raising `TypeError`. Real `infer()` also executed 16 redundant TreeSHAP calls. | Added `__float__` to `ModelInferenceResult`, added `predict_proba()` to `LightGBMService` and `DemoModelService`, updated `_get_model_fn` to prioritize `predict_proba`. | **VERIFIED PASS** (`test_detector_with_real_demo_model_service_regression`, `test_detector_with_real_lightgbm_service_regression`) |
| **D-05** | P2 (Medium) | `M4CrossViewDetector` | `backend/src/x_sentinel/detection/m4_cross_view.py` (L96-101) | `_extract_3_views` checked `isinstance(view_scores, (list, tuple))`, rejecting `np.ndarray` input of length 3 with `TypeError`. | Generalized sequence check to accept any sequence/array with `__len__ == 3` and `__iter__`. | **VERIFIED PASS** (`test_detector_supports_numpy_array_regression`) |
| **D-06** | P3 (Low) | `DetectorConfig` Loader | `backend/src/x_sentinel/detection/config.py` (L137-205) | `m_data.get("enabled", True)` returned `None` when YAML explicitly contained `null`, causing `bool(None) == False`. | Implemented `_parse_bool` helper with safe defaults and string parsing. | **VERIFIED PASS** (`test_load_config_with_explicit_null_and_string_booleans`) |

---

### Detailed Defect Reports

#### D-01: DetectorPipeline View Slicing AttributeError
- **Symptom**: Calling `DetectorPipeline.evaluate()` or `DetectorPipeline.scores()` with an `IndicesSpec`-based `ViewMap` failed with:
  `AttributeError: 'IndicesSpec' object has no attribute 'start'`.
- **Root Cause**: `pipeline.py` assumed `target_view_map.structural`, `behavioral`, and `metadata` were instances of `SliceSpec`, violating the `ViewSpec` polymorphic union contract (`SliceSpec | IndicesSpec`) established in BE-04.
- **Remediation**: Replaced manual slice dict construction with `target_view_map.split(shap)` which polymorphically delegates to each spec's `.extract()` method.
- **Regression Test**: `TestDetectorPipelineContract.test_pipeline_with_indices_spec_view_map_regression`.

#### D-02: AnalysisService View Slicing AttributeError
- **Symptom**: Calling `AnalysisService.analyze_vector()` with an `IndicesSpec` view map failed with `AttributeError`.
- **Root Cause**: `analysis_service.py` sliced `shap` using `[self.view_map.structural.start : self.view_map.structural.stop]`.
- **Remediation**: Replaced slicing with `self.view_map.split(shap)`.
- **Regression Test**: `test_analysis_service_with_indices_spec_regression`.

#### D-03: M3ViewDetector Fallback Slice Access
- **Symptom**: When `view_map` had attributes `structural`, `behavioral`, `metadata` but did not implement `.split()`, `_prepare_views` directly read `.start` and `.stop`.
- **Root Cause**: Missing check for `.extract()` on individual view specifications.
- **Remediation**: Implemented local helper `_extract_view(spec)` in `_prepare_views` checking `hasattr(spec, "extract")` before falling back to `.start:.stop`.
- **Regression Test**: Full M3 test suite verified.

#### D-04: M2 Tabular STRIP Incompatible with Real Model Service Outputs & TreeSHAP Overhead
- **Symptom**: `M2StripDetector.detect(x, model_service=service)` raised `TypeError: float() argument must be a string or a real number, not 'ModelInferenceResult'` when passing a real `LightGBMService` or `DemoModelService`. Test suite previously passed only because test fixtures used a mock returning a raw 2-tuple `(0.75, shap)`.
- **Secondary Impact**: Calling `infer()` on 16 convex-mixed vectors computed full TreeSHAP explanations for all 16 perturbations, taking >15 seconds per detection and consuming massive CPU time. Tabular STRIP only requires the predicted malware probability $P(y=1|x)$, not feature attributions.
- **Remediation**:
  1. Implemented `__float__` on `ModelInferenceResult` returning `self.score`.
  2. Implemented fast `predict_proba(vector) -> float` on both `LightGBMService` and `DemoModelService`.
  3. Updated `M2StripDetector._get_model_fn` to inspect and prioritize `model_service.predict_proba` over `model_service.infer`.
- **Regression Test**: `test_detector_with_real_demo_model_service_regression`, `test_detector_with_real_lightgbm_service_regression`, `test_pipeline_with_real_demo_model_service_regression`, `test_pipeline_with_real_lightgbm_service_regression`.

#### D-05: M4 Cross-View Detector Rejection of NumPy Arrays
- **Symptom**: Passing a 3-element `numpy.ndarray` to `M4CrossViewDetector.detect()` raised `TypeError: Invalid view_scores type: <class 'numpy.ndarray'>`.
- **Root Cause**: `_extract_3_views` used `isinstance(view_scores, (list, tuple))`.
- **Remediation**: Updated sequence type check to verify `__len__ == 3` and `__iter__` on non-string/non-bytes objects.
- **Regression Test**: `TestM4CrossViewDetectorClass.test_detector_supports_numpy_array_regression`.

#### D-06: Detector Config Parser Boolean Parsing Null Pointer Defect
- **Symptom**: When a YAML config contained explicit nulls (`enabled: null`), `m_data.get("enabled", True)` returned `None`, which `bool(None)` evaluated to `False` instead of honoring the default or raising validation error.
- **Root Cause**: Unsafe dict get pattern combined with standard Python `bool()` behavior on `None`.
- **Remediation**: Implemented `_parse_bool(val, default)` helper handling `None`, booleans, and string representations (`"true"`, `"false"`, `"yes"`, `"no"`, `"1"`, `"0"`).
- **Regression Test**: `TestDetectorConfigLoading.test_load_config_with_explicit_null_and_string_booleans`.
