# PLAN-BE-07 — Fusion, D0/D1 Calibration & Decision

## Objective
Version fusion strategy, thresholds and decision policy.

## Status: PASS

## Scope

- Define or implement the smallest canonical slice for this plan.
- Keep detector science, platform persistence and Jev AI authority boundaries explicit (Zero runtime AI/LLM dependencies).
- Update baseline/change-control docs when assumptions change.

## Primary files
- `backend/src/x_sentinel/fusion/__init__.py`
- `backend/src/x_sentinel/fusion/config.py`
- `backend/src/x_sentinel/fusion/calibration.py`
- `backend/src/x_sentinel/fusion/engine.py`
- `backend/src/x_sentinel/fusion/decision.py`
- `backend/src/x_sentinel/fusion/golden_cases.py`
- `configs/detector.yaml`
- `configs/fusion.demo.yaml`
- `configs/fusion.scientific.yaml`
- `artifacts/calibration/d1_calibration.json`
- `backend/tests/test_be07_calibration.py`
- `backend/tests/test_be07_threshold_provenance.py`
- `backend/tests/test_be07_fusion_engine.py`
- `backend/tests/test_be07_decision_golden_cases.py`
- `backend/tests/test_be07_integration.py`

## Task sequence

1. [x] Confirm upstream dependencies and unresolved P0 items (BE-01 through BE-06 all PASS; 265 baseline tests verified).
2. [x] Freeze interfaces/config/schema for this slice (`FusionConfig`, `CalibrationConfig`, `FusionLayerConfig`, `load_fusion_config`, `FusionEngine`, `ScientificFusion`, `D0Calibration`, `D1Calibration`, `CalibrationArtifact`, `DecisionPolicy`, `ThresholdProvenance`, `DecisionResult`).
3. [x] Implement or update code and configuration (`engine.py`, `calibration.py`, `decision.py`, `config.py`, `golden_cases.py`, `__init__.py`, `configs/detector.yaml`, `configs/fusion.demo.yaml`, `configs/fusion.scientific.yaml`, `artifacts/calibration/d1_calibration.json`).
4. [x] Add positive, negative, calibration, provenance, and golden decision tests (72 targeted tests across 5 test modules, 337 passed across full repo suite).
5. [x] Produce evidence/artifact hashes where applicable (frozen `d1_calibration.json` payload SHA-256: `e899ad25ef88e267281503012803421816d27b720269f94bd3aca3e64c99fcd3`).
6. [x] Update traceability and readiness documentation (`PLAN-BE-07.md`, `17_TRACEABILITY_MATRIX.md`, `18_FEATURE_MATRIX.md`, `24_BASELINE_READINESS_REPORT.md`).

## Acceptance
- [x] calibration test:
  - D0 alert budget mode verified with operational threshold.
  - D1 empirical quantile threshold calibration targeting FPR $\le 0.01$ verified.
  - Wilson score 95% confidence interval formula and boundary verification ($[0.0054, 0.0183]$ at $N=1000$).
  - Calibration artifact generation, serialization, and cryptographic SHA-256 verification verified.
  - Fail-closed security against tampered artifacts (`CalibrationIntegrityError`) and missing scientific artifacts (`CalibrationUnresolvedError`).
  - 17 passed tests in `test_be07_calibration.py`.
- [x] threshold provenance:
  - Provenance model (`threshold_id`, `value`, `mode`, `source`, `config_hash`, `artifact_hash`, `wilson_ci`).
  - Strict domain validation ($\tau \in [0.0, 1.0]$, $\tau_{\text{quarantine}} \ge \tau_{\text{alert}}$).
  - Exact boundary behavior ($<, ==, >$) verified on alert and quarantine thresholds.
  - 12 passed tests in `test_be07_threshold_provenance.py`.
- [x] decision golden cases:
  - 8 canonical golden cases spanning benign, sub-threshold, exact alert boundary, suspicious alert, exact quarantine boundary, severe trojan, demo mode isolation, and D1 false alarm suppression.
  - Deterministic evaluation and batch vs single consistency verified.
  - 10 passed tests in `test_be07_decision_golden_cases.py`.
- [x] fusion engine & mathematical verification:
  - Convex combination $S = \sum w_i s_i$ with normalized weights $\sum w_i = 1.0$.
  - Logistic regression fusion $S = \sigma(z)$.
  - Max signal anomaly fusion $S = \max(s_i)$.
  - Signal input validation contract (dict, SignalResult, sequence; finite floats in $[0, 1]$; case-insensitivity).
  - 28 passed tests in `test_be07_fusion_engine.py`.
- [x] pipeline integration:
  - End-to-end integration from `DetectorPipeline` through `FusionEngine` to `DecisionPolicy`.
  - Zero runtime Jev AI / LLM dependencies.
  - SQL Server database check constraint compatibility (`decision IN ('unknown','pass','alert','quarantine')`).
  - 5 passed tests in `test_be07_integration.py`.

## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.

## Recommended next eligible plan
`BE-08` (Audit, Evidence & Artifact Contracts).
