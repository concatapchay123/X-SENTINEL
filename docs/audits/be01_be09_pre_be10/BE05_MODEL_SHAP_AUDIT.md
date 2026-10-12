# X-SENTINEL V3 — MODEL & SHAP SERVICE AUDIT REPORT (BE-05)
## LightGBM Inference & Local TreeSHAP Service

**Audit Scope**: PLAN-BE-05  
**Auditor**: Independent Technical Quality Assurance Team  
**Date**: October 12, 2026  
**Status**: VERIFIED PASS  

---

## 1. Model Loading, Identity & Artifact Integrity

### 1.1. Model Artifact Verification
- **Artifact Path**: `datasets/ember2018/ember_model_2018.txt`
- **Model Version**: `ember2018-v1`
- **Algorithm**: LightGBM GBDT (1,000 trees, 1,470 leaves, learning rate 0.05, objective binary sigmoid).
- **Features**: Exactly 2,381 features (`num_feature() == 2381`).
- **Cryptographic SHA-256 Digest**:
  - Computed: `509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2`
  - Expected (`configs/model.ember2018.yaml`): `509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2`
  - Result: EXACT MATCH.
- **Integrity Enforcement**:
  - Missing artifact raises `ModelArtifactNotFoundError`.
  - Checksum mismatch raises `ModelIntegrityError`.
  - Corrupted model format raises `ModelIntegrityError`.
  - Wrong feature dimension raises `ModelCompatibilityError`.

### 1.2. Scientific vs Demo Separation
- **Demo Adapter (`DemoModelService`)**:
  - Deterministic pseudo-model for rapid offline testing and frontend prototyping.
  - Generates scores based on features with zero LightGBM dependency.
  - Distinctly flagged with `demo_mode=True` and `status="DEMO_ONLY"`.
  - Strict contract: Forbidden from producing scientific evidence (`ScientificEvidenceRejectedError`).
- **Scientific Adapter (`LightGBMService`)**:
  - Direct native execution of official EMBER 2018 LightGBM model.
  - Returns `ModelInferenceResult` containing `score` ($P(y=1|x) \in [0.0, 1.0]$) and local `shap_values` (2,381 floats).
  - Implements fast `predict_proba(vector)` for Tabular STRIP (M2) to avoid unnecessary TreeSHAP calculation overhead.

---

## 2. TreeSHAP Explanation Service Audit

### 2.1. SHAP Output Space & Mathematical Correctness
- **Explainer Implementation**: `shap.TreeExplainer(booster, model_output="raw")`.
- **Output Space**: Margin space (log-odds / logit space) matching TreeSHAP exact additive property:
  $$\sum_{j=1}^{2381} \phi_j(x) = f(x) - \mathbb{E}[f(x)]$$
  where $f(x)$ is the raw margin output of the booster and $\mathbb{E}[f(x)]$ is `expected_value`.
- **Verification of Additivity**:
  - In `backend/tests/test_be05_lightgbm_shap_service.py`:
  - `test_shap_exact_additivity_property`: Verified $|\sum \phi_j + \text{base\_value} - \text{margin}| < 10^{-4}$.
  - Passed across single and batch inferences.
- **Output Dimensions**:
  - Length of `shap_values`: exactly 2,381 floats.
  - Feature correspondence: strictly aligned $1:1$ with canonical feature indices $[0..2380]$.

### 2.2. Thread-Safety & In-Memory Model Cache
- **Model Cache**: `_MODEL_CACHE` keyed by `(resolved_path, sha256)` preventing redundant file I/O.
- **Concurrency**: Verified in `test_concurrent_inference_thread_safety` using `ThreadPoolExecutor(max_workers=4)` running simultaneous inferences. Zero race conditions or state pollution detected.

---

## 3. Conclusion & Gate Decision

| Check | Requirement | Result | Status |
|---|---|---|---|
| Model Checksum | SHA-256 `509de4a8...` | Verified match | **PASS** |
| Feature Dimension | Exactly 2,381 features | Verified | **PASS** |
| Checksum Enforcement | Raise `ModelIntegrityError` on mismatch | Verified | **PASS** |
| Fast `predict_proba` | Fast probability without TreeSHAP | Verified | **PASS** |
| SHAP Dimensions | Exactly 2,381 attributions | Verified | **PASS** |
| SHAP Additivity | Margin space additivity within $10^{-4}$ | Verified | **PASS** |
| Thread Safety | Concurrent execution safe | Verified | **PASS** |
| Scientific Separation | Demo mode isolated from scientific claims | Verified | **PASS** |

**BE-05 MODEL & SHAP AUDIT VERDICT**: **PASS**
