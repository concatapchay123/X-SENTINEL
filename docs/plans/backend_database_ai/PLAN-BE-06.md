# PLAN-BE-06 — M1–M5 Detector Core

## Objective
Implement/freeze detector modules without AI dependencies.

## Status: PASS

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit (Zero runtime AI/LLM dependencies).
- Update baseline/change-control docs when assumptions change.

## Primary files
- `backend/src/x_sentinel/detection/__init__.py`
- `backend/src/x_sentinel/detection/config.py`
- `backend/src/x_sentinel/detection/m1_tadr.py`
- `backend/src/x_sentinel/detection/m2_strip.py`
- `backend/src/x_sentinel/detection/m3_view.py`
- `backend/src/x_sentinel/detection/m4_cross_view.py`
- `backend/src/x_sentinel/detection/m5_semantic.py`
- `backend/src/x_sentinel/detection/pipeline.py`
- `configs/detector.yaml`
- `configs/m5_rules.json`
- `backend/tests/test_be06_m1_tadr.py`
- `backend/tests/test_be06_m2_strip.py`
- `backend/tests/test_be06_m3_view.py`
- `backend/tests/test_be06_m4_cross_view.py`
- `backend/tests/test_be06_m5_semantic.py`
- `backend/tests/test_be06_detector_pipeline.py`

## Task sequence

1. [x] Confirm upstream dependencies and unresolved P0 items (BE-01 PASS, BE-02 PASS, BE-03 PASS, BE-04 PASS [2,381 features/views], BE-05 PASS [LightGBM/TreeSHAP] verified).
2. [x] Freeze interfaces/config/schema for this slice (`SignalResult`, `M1Config`..`M5Config`, `DetectorConfig`, `load_detector_config`, `compute_detector_config_hash`, `M1TADRDetector`, `M2StripDetector`, `M3ViewDetector`, `M4CrossViewDetector`, `M5SemanticPlausibilityDetector`, `DetectorPipeline`).
3. [x] Implement or update code and configuration (`m1_tadr.py`, `m2_strip.py`, `m3_view.py`, `m4_cross_view.py`, `m5_semantic.py`, `pipeline.py`, `config.py`, `__init__.py`, `configs/detector.yaml`, `configs/m5_rules.json`).
4. [x] Add positive, negative, and edge-case unit tests per signal (102 targeted tests across 6 test modules, 262 passed across full repo suite).
5. [x] Produce evidence/artifact hashes where applicable (frozen `m5_rules.json` SHA-256: `2e8c599aa9fded31c8d27eb0d96f45743a087572f696bc8e3bdb0f69d5ca184d`; detector configuration SHA-256: `b43c4960572f16ac06d046cc6e8016b97b96feab8cfcdecd3a998429459d8830`).
6. [x] Update traceability and readiness documentation (`PLAN-BE-06.md`, `17_TRACEABILITY_MATRIX.md`, `24_BASELINE_READINESS_REPORT.md`).

## Acceptance
- [x] unit tests per signal:
  - M1 TADR: 19 passed (`test_be06_m1_tadr.py`)
  - M2 STRIP: 24 passed (`test_be06_m2_strip.py`)
  - M3 View: 16 passed (`test_be06_m3_view.py`)
  - M4 Cross-View: 17 passed (`test_be06_m4_cross_view.py`)
  - M5 Semantic: 16 passed (`test_be06_m5_semantic.py`)
  - Pipeline Integration: 10 passed (`test_be06_detector_pipeline.py`)
- [x] formula/config traceability:
  - M1: Canonical Top-k Attribution Dominance Ratio (Severi et al., USENIX Security 2021) $\text{TADR}_k(S) = \frac{\sum_{i=1}^k |s_{(i)}|}{\sum_i |s_i|}$, where $|s_{(i)}|$ denotes the $i$-th largest absolute SHAP feature attribution, parameterized with $k \ge 1$ (default $k=1$) and division-by-zero protection $\epsilon=10^{-12}$, traceable to `configs/detector.yaml` and `backend/src/x_sentinel/detection/config.py`. The legacy documentation typo $S_{\text{M1}} = \frac{|\Delta y|}{|\Delta y_{\text{ref}}| + \epsilon}$ (which erroneously stated a perturbation drift ratio) is formally retracted and superseded by the canonical Top-k TADR specification.
  - M2: Perturbation blending $(1-\alpha)x + \alpha x_b$, binary entropy $H(p) = -p\log_2 p - (1-p)\log_2(1-p)$, $S_{\text{M2}} = \frac{1}{N}\sum_{i=1}^N H(p_i)$ with $N=16, \alpha=0.2, \text{seed}=42$ traceable to `configs/detector.yaml`.
  - M3: Absolute SHAP sum concentration per view $c_v = \sum_{j \in V_v} |\phi_j|$, distribution $p_v = \frac{c_v}{\sum c_k}$, entropy $H = -\sum p_v \log_2 p_v$, $S_{\text{M3}} = 1 - \frac{H}{\log_2 K}$ traceable to `configs/detector.yaml`.
  - M4: Canonical symmetric cross-view disagreement $S_{\text{M4}} = 0.5 \sum_{i<j} |y_i - y_j|$ in $[0, 1]$ per ADR-005, plus 4 ablation strategies (`view_std`, `behavioral_metadata_gap`, `full_vs_behavioral_gap`, `max_pairwise_difference`) traceable to `configs/detector.yaml`.
  - M5: Physical PE invariant rule evaluation with fail-closed cryptographic integrity verification against SHA-256 `2e8c599aa9fded31c8d27eb0d96f45743a087572f696bc8e3bdb0f69d5ca184d`.

## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.

## Recommended next eligible plan
`BE-07` (Fusion & Uncertainty Calibration).


## Current Implementation Status

- **Verified Implementation Status:** `COMPLETED_VERIFIED`
- **Exact Source File Paths:**
  - `backend/src/x_sentinel/detection/config.py`
  - `backend/src/x_sentinel/detection/m1_tadr.py`
  - `backend/src/x_sentinel/detection/m2_strip.py`
  - `backend/src/x_sentinel/detection/m3_view.py`
  - `backend/src/x_sentinel/detection/m4_cross_view.py`
  - `backend/src/x_sentinel/detection/m5_semantic.py`
  - `backend/src/x_sentinel/detection/pipeline.py`
- **Associated Test Suites:**
  - `backend/tests/test_be06_m1_tadr.py` (19 passed)
  - `backend/tests/test_be06_m2_strip.py` (24 passed)
  - `backend/tests/test_be06_m3_view.py` (16 passed)
  - `backend/tests/test_be06_m4_cross_view.py` (17 passed)
  - `backend/tests/test_be06_m5_semantic.py` (16 passed)
  - `backend/tests/test_be06_detector_pipeline.py` (10 passed)
  - `backend/tests/test_m1.py`
- **Empirical Artifacts:**
  - `configs/m5_rules.json` (physical PE domain invariant rules with SHA-256 integrity verification: `2e8c599aa9fded31c8d27eb0d96f45743a087572f696bc8e3bdb0f69d5ca184d`)
  - `configs/detector.yaml` (M1–M5 detector core configuration)
- **Operational Boundaries & Verified Limitations:**
  - Invariant 05 strictly verified (zero runtime AI dependency). M5 evaluation uses preliminary structural heuristics; STRIP stochasticity locked to pseudo-random seed (`seed=42`) with 32-sample frozen benign pool (`be14_m2_strip_pool_v1`).
  - M1 TADR Top-k attribution dominance: Formally implemented in `backend/src/x_sentinel/detection/m1_tadr.py` and `config.py` with parameter $k \ge 1$ (default $k=1$). The legacy documentation typo $|\Delta y| / |\Delta y_{\text{ref}}|$ has been formally retracted.
  - M5 Semantic Plausibility Polarity: M5 detector primary score aligns to anomaly/suspicion score $1.0 - \text{plausibility\_score}$ (0.0 clean, 1.0 violating) for mathematical consistency with M1–M4 in fusion, while preserving both `plausibility_score` and `anomaly_score` in diagnostics.
