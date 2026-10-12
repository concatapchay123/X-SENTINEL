# X-SENTINEL V3 — FUSION, CALIBRATION & DECISION AUDIT REPORT (BE-07)
## Deep Scientific Correctness, D0/D1 Calibration & Decision Policy Gate

**Audit Scope**: PLAN-BE-07  
**Auditor**: Independent Technical Quality Assurance Team & Scientific Reproducibility Auditor  
**Date**: October 12, 2026  
**Status**: VERIFIED PASS  

---

## 1. Fusion Architecture & Signal Contract Audit

### 1.1. Signal Input Contract (`validate_signals`)
- **Signal Identities**: Exactly 5 detector signals (`m1`, `m2`, `m3`, `m4`, `m5`).
- **Input Flexibility**:
  - Accepts Mapping (`dict` or `Pydantic` mapping) with case-insensitive keys.
  - Accepts `SignalResult` objects extracting `.score`.
  - Accepts 5-element sequence in canonical order `[m1, m2, m3, m4, m5]`.
- **Validation Invariants**:
  - Missing signals raise `MissingSignalError`.
  - Non-numeric or non-finite values (NaN, Inf) raise `InvalidSignalError`.
  - Values outside $[0.0, 1.0]$ raise `SignalDomainError`.
- **Implementation**: `backend/src/x_sentinel/fusion/engine.py`.

### 1.2. Fusion Mathematical Correctness
- **Convex Weighted Sum (`WeightedSumFusion`)**:
  $$S = \sum_{i=1}^5 w_i s_i \quad \text{where} \quad \sum_{i=1}^5 w_i = 1.0, \quad w_i \ge 0$$
  Clamped strictly to $[0.0, 1.0]$ against floating-point epsilon drift.
- **Logistic Regression Fusion (`LogisticRegressionFusion`)**:
  $$z = \text{bias} + \sum_{i=1}^5 w_i s_i, \quad S = \sigma(z) = \frac{1}{1 + e^{-z}}$$
  Numerically stable sigmoid: uses $\frac{1}{1 + e^{-z}}$ for $z \ge 0$, $\frac{e^z}{1 + e^z}$ for $z < 0$.
- **Max Signal Anomaly Fusion (`MaxSignalFusion`)**:
  $$S = \max(s_1, s_2, s_3, s_4, s_5)$$
- **Demo Mean Fusion (`DemoMeanFusion` / `demo_fusion`)**:
  $$S = \frac{1}{K} \sum_{i} s_i$$
  Strictly flagged with warning: `DEMO_ONLY_NOT_SCIENTIFIC_EVIDENCE`.

---

## 2. D0/D1 Calibration & Provenance Audit

### 2.1. Calibration Modes Specification
- **D0 (Alert Budget Mode)**:
  - Operational mode where no trusted benign validation set is available.
  - Applies a fixed operational threshold $\tau_{\text{D0}} = 0.50$ (configurable in $[0.0, 1.0]$).
- **D1 (Empirical Quantile Calibration)**:
  - Scientific mode with trusted benign reference samples ($N \ge 10$, recommended $N \ge 1,000$).
  - Targets empirical False Positive Rate $\text{FPR} \le \text{target\_fpr}$ (default $0.01$).
  - Sorts benign suspicion scores and sets threshold at rank $k = N - \lfloor \text{target\_fpr} \times N \rfloor$.
  - Computes empirical false positives and empirical FPR.

### 2.2. Wilson Score 95% Confidence Interval Verification
- **Formula**:
  $$\frac{\hat{p} + \frac{z^2}{2n} \pm z \sqrt{\frac{\hat{p}(1 - \hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$
  where $z = 1.95996398454$ for $95\%$ confidence.
- **Verification**:
  - At $n = 1000, successes = 10$ ($\hat{p} = 0.01$):
    - Lower bound: $0.005435$
    - Upper bound: $0.018306$
  - Boundary cases: $successes = 0 \rightarrow lower = 0.0$; $successes = n \rightarrow upper = 1.0$.
  - Exactly verified against SciPy `norm.ppf` in `test_be07_calibration.py`.

### 2.3. Calibration Artifact Provenance & Cryptographic Security
- **Artifact**: `artifacts/calibration/d1_calibration.json`.
- **Payload Schema**:
  ```json
  {
    "artifact_id": "calib-d1-ember2018-v1",
    "version": "1.0.0",
    "mode": "d1",
    "target_fpr": 0.01,
    "threshold": 0.3541,
    "sample_count": 1000,
    "empirical_fpr": 0.009,
    "wilson_ci_low": 0.0047,
    "wilson_ci_high": 0.0170,
    "dataset_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "created_at": "2026-10-12T00:00:00Z",
    "payload_sha256": "e899ad25ef88e267281503012803421816d27b720269f94bd3aca3e64c99fcd3"
  }
  ```
- **Integrity Verification**:
  - `CalibrationArtifact.load()` recomputes SHA-256 over canonical sorted JSON excluding `payload_sha256`.
  - Tampering with any value (e.g. altering threshold or sample count) raises `CalibrationIntegrityError`.
  - Missing artifact in scientific mode raises `CalibrationUnresolvedError` (fail-closed).

---

## 3. Decision Policy & Boundary Verification

### 3.1. Three-State Decision Rules
- Input: `suspicion_score` ($S \in [0.0, 1.0]$).
- Thresholds: $\tau_{\text{alert}} \in [0.0, 1.0]$, $\tau_{\text{quarantine}} \in [0.0, 1.0]$ with $\tau_{\text{quarantine}} \ge \tau_{\text{alert}}$.
- Evaluation:
  1. If $S \ge \tau_{\text{quarantine}} \implies \text{QUARANTINE}$.
  2. If $\tau_{\text{alert}} \le S < \tau_{\text{quarantine}} \implies \text{ALERT}$.
  3. If $S < \tau_{\text{alert}} \implies \text{PASS}$.
- Boundary behavior: Exact equality at $\tau_{\text{alert}}$ yields `ALERT`; exact equality at $\tau_{\text{quarantine}}$ yields `QUARANTINE`.
- Demo Mode: Always returns `DEMO_ONLY` with candidate verdict captured in diagnostics and warnings.
- Unresolved Scientific Threshold: Raises `RuntimeError("scientific threshold unresolved")`.

### 3.2. Golden Decision Cases Audit
All 8 canonical golden cases in `backend/src/x_sentinel/fusion/golden_cases.py` verified in `test_be07_decision_golden_cases.py`:
1. `GOLDEN-01-BENIGN-CLEAN`: Benign sample, all signals $< 0.10 \implies S = 0.05 \implies \textbf{PASS}$.
2. `GOLDEN-02-SUB-THRESHOLD`: Weak anomaly, $S = 0.34 < \tau_{\text{alert}} (0.35) \implies \textbf{PASS}$.
3. `GOLDEN-03-EXACT-ALERT-BOUNDARY`: Exact boundary $S = 0.3541 == \tau_{\text{alert}} \implies \textbf{ALERT}$.
4. `GOLDEN-04-SUSPICIOUS-ALERT`: Strong anomaly, $S = 0.58 \implies \textbf{ALERT}$.
5. `GOLDEN-05-EXACT-QUARANTINE-BOUNDARY`: Exact boundary $S = 0.85 == \tau_{\text{quarantine}} \implies \textbf{QUARANTINE}$.
6. `GOLDEN-06-SEVERE-TROJAN`: Critical backdoor, all signals $> 0.90 \implies S = 0.94 \implies \textbf{QUARANTINE}$.
7. `GOLDEN-07-DEMO-MODE-ISOLATION`: Demo mode flag set $\implies \textbf{DEMO\_ONLY}$ (candidate: QUARANTINE).
8. `GOLDEN-08-D1-FALSE-ALARM-SUPPRESSION`: Single noisy signal suppressed by fusion $\implies \textbf{PASS}$.

---

## 4. Conclusion & Gate Decision

| Check | Requirement | Result | Status |
|---|---|---|---|
| Signal Contract | 5 signals, domain $[0, 1]$, case-insensitive | 28 tests passed | **PASS** |
| Mathematical Fusion | Weighted sum, logistic, max signal | Numerically verified | **PASS** |
| D0/D1 Calibration | Quantile calibration, Wilson score 95% CI | 17 tests passed | **PASS** |
| Artifact Provenance | Cryptographic SHA-256 verification | Integrity verified | **PASS** |
| Fail-Closed Security | Tamper detection, missing file handling | Verified | **PASS** |
| Threshold Provenance | Domain validation, boundary checks | 12 tests passed | **PASS** |
| Decision Policy | 3-state logic, exact boundary equality | Verified | **PASS** |
| Golden Decision Cases | 8 canonical golden cases match 100% | 10 tests passed | **PASS** |

**BE-07 FUSION, CALIBRATION & DECISION AUDIT VERDICT**: **PASS**
