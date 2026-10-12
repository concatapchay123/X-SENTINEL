# X-SENTINEL V3 — DETECTOR CORE AUDIT REPORT (BE-06)
## M1–M5 Detector Modules & Unified Pipeline

**Audit Scope**: PLAN-BE-06  
**Auditor**: Independent Technical Quality Assurance Team  
**Date**: October 12, 2026  
**Status**: VERIFIED PASS  

---

## 1. M1–M5 Mathematical Formulation & Implementation Audit

### 1.1. M1: Top-1 Attribution Dominance Ratio (TADR)
- **Mathematical Specification**:
  $$\text{TADR}(S) = \frac{\max_i |s_i|}{\sum_{i} |s_i|}$$
  where $S = (s_1, \dots, s_{2381})$ is the local TreeSHAP attribution vector.
- **Edge Conditions**:
  - If $\sum_i |s_i| \le \epsilon$ ($\epsilon = 10^{-12}$), returns $0.0$ to prevent division by zero.
  - Bounded strictly in $[0.0, 1.0]$.
  - Input validation: verifies numeric values, rejects NaN/Inf, requires non-empty sequence.
- **Implementation**: `backend/src/x_sentinel/detection/m1_tadr.py` (`m1_tadr` function and `M1TADRDetector` class).
- **Diagnostics**: Reports `top_feature_index`, `top_feature_abs_shap`, `total_abs_shap`.
- **Verification Status**: 21 passed tests in `test_be06_m1_tadr.py`.

### 1.2. M2: Tabular STRIP (STRong Intentional Perturbation)
- **Mathematical Specification**:
  - Perturbation of input $x$ with benign reference vector $x_{\text{benign}}$ drawn from pool:
    $$x_{\text{perturbed}} = (1 - \alpha) x + \alpha x_{\text{benign}} \quad (\alpha = 0.2, N = 16)$$
  - Model evaluation: $p_i = P(y=1 | x_{\text{perturbed}}^{(i)})$.
  - Binary Shannon entropy:
    $$H(p_i) = - p_i \log_2(p_i) - (1 - p_i) \log_2(1 - p_i)$$
  - Average entropy: $\bar{H} = \frac{1}{N} \sum_{i=1}^N H(p_i)$.
  - Score: $M_2 = 1.0 - \bar{H}$ (when `invert_entropy=True`, low entropy $\rightarrow$ high trojan suspicion).
- **Optimization Audit**:
  - Defect D-04 resolved: `M2StripDetector` prioritizes `predict_proba` over `infer()`, eliminating redundant 16-fold TreeSHAP calculations and reducing detection latency from $>15$s to $<0.05$s.
- **Verification Status**: 24 passed tests in `test_be06_m2_strip.py`.

### 1.3. M3: View Contribution & Concentration
- **Mathematical Specification**:
  - Normalized absolute attribution per semantic view $v \in \{\text{structural}, \text{behavioral}, \text{metadata}\}$:
    $$C(v) = \frac{\sum_{j \in v} |s_j|}{\sum_{u} \sum_{j \in u} |s_j|}$$
  - View concentration metric:
    $$M_3 = \max_{v} C(v)$$
  - Shannon view entropy: $H(C) = - \sum_{v: C(v) > \epsilon} C(v) \log_2(C(v))$.
- **Polymorphic Spec Compatibility**:
  - Defect D-03 resolved: `_prepare_views` supports both `SliceSpec` and `IndicesSpec` via polymorphic `.split()` and `.extract()`.
- **Verification Status**: 16 passed tests in `test_be06_m3_view.py`.

### 1.4. M4: Symmetric Cross-View Disagreement
- **Mathematical Specification (ADR-005)**:
  - For view prediction signals $y_1, y_2, y_3 \in [0.0, 1.0]$:
    $$\text{Disagreement} = 0.5 \times (|y_1 - y_2| + |y_2 - y_3| + |y_3 - y_1|)$$
- **Mathematical Invariants**:
  - Strictly symmetric under all 6 permutations of $(y_1, y_2, y_3)$.
  - Exactly $0.0$ when all views agree ($y_1 = y_2 = y_3$).
  - Exactly $1.0$ under maximal one-sided divergence (e.g. $[1, 0, 0]$).
  - Bounded in $[0.0, 1.0]$.
- **Sequence Compatibility**:
  - Defect D-05 resolved: supports dictionaries, lists, tuples, and length-3 `numpy.ndarray`.
- **Verification Status**: 18 passed tests in `test_be06_m4_cross_view.py`.

### 1.5. M5: Semantic Invariant Plausibility
- **Specification**: Evaluates physical PE header domain invariants against the EMBER 2,381 feature vector.
- **Rules Artifact**: `configs/m5_rules.json`.
- **Cryptographic Verification**:
  - Verified with `hashlib.sha256(raw_bytes)`.
  - Mismatch raises `M5RulesIntegrityError`.
- **Verification Status**: 16 passed tests in `test_be06_m5_semantic.py`.

---

## 2. Unified Pipeline (`DetectorPipeline`)

### 2.1. Architecture & Execution Flow
- Coordinates end-to-end evaluation:
  1. Validates input 2,381-vector via `validate_vector`.
  2. Obtains model inference score and local TreeSHAP attributions.
  3. Executes M1 TADR on SHAP attributions.
  4. Executes M2 Tabular STRIP on input vector using benign pool and model `predict_proba`.
  5. Executes M3 View Concentration on SHAP attributions partitioned by view map.
  6. Executes M4 Cross-View Disagreement on 3-view scores.
  7. Executes M5 Semantic Invariant Plausibility on input vector.
- Returns `dict[str, SignalResult]` with keys `m1`, `m2`, `m3`, `m4`, `m5`.

### 2.2. Zero AI Runtime Dependency Invariant
- **Rule**: `DetectorPipeline` contains zero imports or runtime calls to Jev AI, LM Studio, or external LLM endpoints.
- **Verification**: Verified under offline conditions and with `XS_JEV_AI_ENABLED=false`.

---

## 3. Conclusion & Gate Decision

| Module | Mathematical Formula | Domain & Range | Verification | Status |
|---|---|---|---|---|
| M1 TADR | $\max \|s_i\| / \sum \|s_i\|$ | $[0.0, 1.0]$ | 21 tests passed | **PASS** |
| M2 STRIP | $1.0 - \bar{H}$ | $[0.0, 1.0]$ | 24 tests passed | **PASS** |
| M3 VIEW | $\max_v C(v)$ | $[0.0, 1.0]$ | 16 tests passed | **PASS** |
| M4 CROSS-VIEW | $0.5 \sum \|y_i - y_j\|$ | $[0.0, 1.0]$ | 18 tests passed | **PASS** |
| M5 SEMANTIC | Invariant Rule Evaluator | $[0.0, 1.0]$ | 16 tests passed | **PASS** |
| Pipeline | Unified Orchestrator | SignalResult dict | 14 tests passed | **PASS** |

**BE-06 DETECTOR CORE AUDIT VERDICT**: **PASS**
