# PLAN-BE-05 — LightGBM & SHAP Model Service

## Objective
Load versioned model, hash artifacts, run inference and local SHAP.

## Status: PASS

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit.
- Update baseline/change-control docs when assumptions change.

## Primary files
- `backend/src/x_sentinel/model/__init__.py`
- `backend/src/x_sentinel/model/lightgbm_service.py`
- `backend/src/x_sentinel/model/shap_service.py`
- `backend/src/x_sentinel/model/demo.py`
- `configs/model.demo.yaml`
- `configs/model.scientific.yaml`
- `configs/model.ember2018.yaml`
- `backend/tests/test_be05_lightgbm_shap_service.py`

## Task sequence

1. [x] Confirm upstream dependencies and unresolved P0 items (BE-01 PASS, BE-02 PASS, BE-03 PASS, BE-04 PASS verified; OQ-02 tracked and guarded by fail-closed enforcement).
2. [x] Freeze interfaces/config/schema for this slice (`LightGBMService`, `DemoModelService`, `SHAPService`, `SHAPExplanation`, `ModelInferenceResult`, `ModelMetadata`, `compute_artifact_sha256`, `load_model_service`).
3. [x] Implement or update code and configuration (`lightgbm_service.py`, `shap_service.py`, `demo.py`, `__init__.py`, `configs/model.demo.yaml`, `configs/model.scientific.yaml`, `configs/model.ember2018.yaml`).
4. [x] Add positive, negative, and edge-case tests (30 targeted tests in `test_be05_lightgbm_shap_service.py`, 157 passed across full repo suite).
5. [x] Produce evidence/artifact hashes where applicable (canonical EMBER 2018 model SHA-256: `509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2`).
6. [x] Update traceability and readiness documentation.

## Acceptance
- [x] model identity test (`test_load_valid_approved_lightgbm_model`, `test_compute_artifact_sha256_matches_canonical`, `test_checksum_mismatch_raises_integrity_error`, `test_dimension_mismatch_raises_compatibility_error`).
- [x] SHAP shape test (`test_shap_explanation_shape_and_alignment`, `test_shap_additivity`, `test_shap_base_value_is_constant_across_samples`).
- [x] demo/scientific separation (`test_demo_mode_output_distinctly_marked`, `test_scientific_service_rejects_demo_mode`, `test_loader_demo_config_rejected_when_demo_disallowed`, `test_no_silent_fallback_when_artifact_tampered`).

## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.

## Recommended next eligible plan
`BE-06` (M1–M5 Detector Core).


## Current Implementation Status

- **Verified Implementation Status:** `COMPLETED_WITH_LIMITATIONS` (Candidate Model Verified / Strict Scientific Promotion Gated)
- **Exact Source File Paths:**
  - `backend/src/x_sentinel/model/lightgbm_service.py`
  - `backend/src/x_sentinel/model/shap_service.py`
  - `backend/src/x_sentinel/model/demo.py`
  - `configs/model.ember2018.yaml`
- **Associated Test Suites:**
  - `backend/tests/test_be05_lightgbm_shap_service.py` (30 passed)
- **Empirical Artifacts:**
  - `configs/model.ember2018.yaml` (SHA-256 `509de4a8...`)
  - `datasets/ember2018/ember_model_2018.txt`
- **Operational Boundaries & Verified Limitations:**
  - `OQ-02` blocker: Promotion to `model.scientific.yaml` is gated pending formal freeze (`expected_sha256: TBD`). Operational model uses EMBER2018 booster (`datasets/ember2018/ember_model_2018.txt`, SHA-256 `509de4a8...`). TreeSHAP execution incurs ~1.2s CPU latency per file; fast-path available without TreeSHAP (~35-41ms).
