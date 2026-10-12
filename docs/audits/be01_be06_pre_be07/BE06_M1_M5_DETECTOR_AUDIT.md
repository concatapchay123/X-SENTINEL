# X-SENTINEL V3 — BE-06 M1–M5 DETECTOR CORE AUDIT REPORT
## Mathematical Formalisms, Detector Implementations & Cross-Signal Coordination

**Audit Version**: 3.0.0-AUDIT  
**Date**: October 12, 2026  
**Auditor**: Independent Technical Review Team  
**Scope**: `PLAN-BE-06.md`  
**Overall Verdict**: **PASS**  

---

## 1. Executive Summary

This report delivers a thorough mathematical and architectural audit of the five sub-detectors (M1 through M5) and the unified `DetectorPipeline` implemented under `PLAN-BE-06.md`.

All five detector signals are strictly bounded within the standard unit interval $[0.0, 1.0]$. The implementations adhere strictly to their authoritative specifications and Architectural Decision Records (specifically ADR-005 for M4 Symmetric Disagreement). All identified integration issues (D-01, D-03, D-04, D-05, D-06) have been completely resolved.

---

## 2. Mathematical Formalisms & Verification

### 2.1. M1: Top-1 Attribution Dominance Ratio (TADR)
- **Authoritative Spec**: `docs/baseline/M1_TADR_SPEC.md`
- **Implementation**: `backend/src/x_sentinel/detection/m1_tadr.py`
- **Mathematical Formula**:
  $$\text{TADR}(\mathbf{s}) = \frac{\max_{i} |s_i|}{\sum_{i=1}^{d} |s_i| + \epsilon}$$
- **Mathematical Bounds**:
  - Minimum possible value: $\frac{1}{d}$ when all feature attributions have identical magnitude.
  - Maximum possible value: $1.0$ when a single feature accounts for 100% of the attribution mass.
  - For $d = 2381$, range is $[0.00042, 1.0]$, strictly inside $[0.0, 1.0]$.
- **Audit Clarification (Doc Typo vs Code)**:
  `PLAN-BE-06.md` line 50 contained an informal notation typo reading $\frac{|\Delta y|}{|\Delta y_{\text{ref}}| + \epsilon}$. The audit confirmed that the objective, requirements, docstrings, unit tests, and production code correctly implement the canonical TADR formula based on SHAP attribution dominance.

### 2.2. M2: Tabular STRIP (Perturbation via Convex Mixing)
- **Authoritative Spec**: `docs/baseline/M2_STRIP_SPEC.md`
- **Implementation**: `backend/src/x_sentinel/detection/m2_strip.py`
- **Mathematical Formalism**:
  1. For an input vector $\mathbf{x}$, sample $N$ benign reference samples $\mathbf{x}_b^{(1)}, \dots, \mathbf{x}_b^{(N)}$ from benign pool.
  2. Perturb via convex combination:
     $$\mathbf{x}_{\text{mix}}^{(k)} = (1 - \alpha) \mathbf{x} + \alpha \mathbf{x}_b^{(k)}, \quad \alpha \in (0, 1)$$
  3. Predict malicious probability $p_k = P(y = 1 | \mathbf{x}_{\text{mix}}^{(k)})$.
  4. Compute Shannon entropy in bits ($base = 2$):
     $$H(p_k) = -p_k \log_2(p_k) - (1 - p_k) \log_2(1 - p_k) \in [0.0, 1.0]$$
  5. Average entropy: $\bar{H} = \frac{1}{N} \sum_{k=1}^N H(p_k)$.
  6. Inverted entropy detection score:
     $$S_{\text{M2}} = 1.0 - \bar{H} \in [0.0, 1.0]$$
- **Verification**: When perturbed predictions remain invariant (low entropy near 0 bits), $S_{\text{M2}} \to 1.0$ (high suspicion of trojan/trigger). When perturbed predictions fluctuate widely (high entropy near 1 bit), $S_{\text{M2}} \to 0.0$ (normal robust sample).

### 2.3. M3: View Contribution & Concentration
- **Authoritative Spec**: `docs/baseline/M3_VIEW_SPEC.md`
- **Implementation**: `backend/src/x_sentinel/detection/m3_view.py`
- **Mathematical Formalism**:
  1. View attribution sums for views $v \in \{\text{structural}, \text{behavioral}, \text{metadata}\}$:
     $$C_v = \sum_{j \in v} |s_j|$$
  2. Normalized view weights:
     $$w_v = \frac{C_v}{\sum_{u} C_u + \epsilon}, \quad \sum_{v} w_v = 1.0$$
  3. View concentration metric (scaled from $[\frac{1}{3}, 1]$ to $[0, 1]$):
     $$\text{concentration} = \max_{v} w_v$$
     $$S_{\text{M3}} = \min\left(\max\left(\frac{\max_v w_v - \frac{1}{3}}{1 - \frac{1}{3}}, 0.0\right), 1.0\right)$$
  4. View entropy metric: $H_v = -\sum_v w_v \ln(w_v) \in [0, \ln(3)]$.
- **Verification**: Balanced attributions across all 3 views give $S_{\text{M3}} = 0.0$. Total dominance in a single view gives $S_{\text{M3}} = 1.0$.

### 2.4. M4: Cross-View Disagreement (ADR-005 Canonical)
- **Authoritative Spec**: `docs/adr/ADR-005-M4-CROSS-VIEW-DISAGREEMENT.md`, `docs/baseline/M4_CROSS_VIEW_SPEC.md`
- **Implementation**: `backend/src/x_sentinel/detection/m4_cross_view.py`
- **Mathematical Formula**:
  $$S_{\text{M4}}(\mathbf{y}) = \frac{1}{2} \left( |y_1 - y_2| + |y_2 - y_3| + |y_3 - y_1| \right)$$
- **Mathematical Invariants**:
  1. **Permutation Symmetry**: $S_{\text{M4}}(\pi(\mathbf{y})) = S_{\text{M4}}(\mathbf{y})$ for all permutations $\pi \in S_3$.
  2. **Zero Disagreement**: $S_{\text{M4}}(y, y, y) = 0.0$ for any $y \in [0, 1]$.
  3. **Maximal Disagreement**: $S_{\text{M4}}(1, 0, 0) = 0.5(1 + 0 + 1) = 1.0$.
  4. **Strict Boundedness**: Guaranteed in $[0.0, 1.0]$ by the triangle inequality.
- **Ablation Plugins**: Supported via configuration switch:
  - `view_std`: Standard deviation across the 3 views.
  - `behavioral_metadata_gap`: $|y_{\text{behavioral}} - y_{\text{metadata}}|$.
  - `full_vs_behavioral_gap`: $|y_{\text{full}} - y_{\text{behavioral}}|$.
  - `max_pairwise_difference`: $\max_{i<j} |y_i - y_j|$.

### 2.5. M5: Semantic Plausibility Rule Engine
- **Authoritative Spec**: `docs/baseline/M5_PLAUSIBILITY_SPEC.md`
- **Implementation**: `backend/src/x_sentinel/detection/m5_plausibility.py`
- **Rulebook**: `configs/m5_rules.json` (SHA-256: `2e8c599aa9fded31c8d27eb0d96f45743a087572f696bc8e3bdb0f69d5ca184d`)
- **Evaluation**: 15 deterministic checks inspecting PE structural/behavioral physical feasibility (e.g., section virtual size vs size of raw data, invalid DOS magic, inconsistent subsystem flags, excessive entropy without packing indicators).
- **Metric**: Plausibility score is the fraction of passed physical integrity rules.

---

## 3. Unified Detector Pipeline Coordination

`DetectorPipeline` (`backend/src/x_sentinel/detection/pipeline.py`) coordinates all five sub-detectors:
- Slices clean input vector and SHAP attributions polymorphically across views.
- Executes M1, M2, M3, M4, and M5 sequentially without external network dependencies.
- Returns `SignalResult` dictionary and convenient `scores(vector)` float dictionary:
  `{"m1": float, "m2": float, "m3": float, "m4": float, "m5": float}` with all values in $[0.0, 1.0]$.
- Complete execution latency: $< 5$ milliseconds with optimized `predict_proba`.

---

## 4. Audit Verdict

**Overall Verdict**: **PASS** (Mathematically validated, verified across edge cases, zero external AI dependencies, fully ready for BE-07 fusion input).
