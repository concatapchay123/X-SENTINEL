# PLAN-BE-14 — Threat Simulation, E0–E5 & Statistics

## Status
**COMPLETED (PASS — CODE, METRICS, STATISTICAL TESTS, BLIND CUSTODY PROTOCOL & FROZEN CANDIDATE E0–E5 SUITE; STRICT SCIENTIFIC SIGN-OFF BLOCKED PENDING OQ-01, OQ-02 & PRE-TRAINED POISONED MODELS)**

## Objective
Produce frozen research runs, raw predictions, statistical significance evaluations, and accepted metrics for X-SENTINEL V3 under a strictly auditable clean-label backdoor threat simulation and blind evaluation protocol.

## Scope

- Freeze the clean-label vector-space threat model (`THREAT_MODEL_SPEC`), Research Questions & Hypotheses (`RQ_HYPOTHESIS_MATRIX`), trigger families (`T-concentrated`, `T-spread`, `T-cross`), and zero-leakage dataset split governance (`DatasetSplitManifest`, `audit_dataset_splits`).
- Implement exact scientific metrics (`compute_auroc`, `compute_fpr`, `compute_recall`, `compute_recall_at_locked_fpr`, `compute_asr`, `compute_latency_summary`) with explicit denominator validation and Wilson 95% confidence intervals.
- Implement paired statistical tests (`mcnemar_paired_test`, `paired_bootstrap_test` with cluster resampling for multi-seed repeated sample IDs, `paired_auroc_comparison` via correlated DeLong and bootstrap, and `holm_bonferroni_correction`).
- Enforce the 3-role Blind Evaluation Protocol (`ATTACK_CONSTRUCTION`, `DEFENSE_DETECTOR`, `EVALUATION_SCORING`), custody path/payload/environment isolation (`BlindCustodyGuard`), cryptographically sealed prediction packages (`BlindPredictionPackage`), and post-hoc threshold tuning prevention (`PostHocTuningForbiddenError`).
- Execute and persist the E0–E5 Frozen Candidate evaluation suite (`artifacts/evaluation/be14_candidate_suite/`) on real EMBER2018 2,381-dim test vectors and `ember_model_2018.txt`, while failing closed (`ExperimentBlockedError`) when `require_strict_scientific_freeze=True` due to unresolved upstream blockers (`OQ-01`, `OQ-02`, `MISSING_POISONED_MODELS`).

## Primary files
- `backend/src/x_sentinel/evaluation/protocol.py`
- `backend/src/x_sentinel/evaluation/metrics.py`
- `backend/src/x_sentinel/evaluation/statistics.py`
- `backend/src/x_sentinel/evaluation/blind.py`
- `backend/src/x_sentinel/evaluation/runner.py`
- `backend/src/x_sentinel/evaluation/__init__.py`
- `backend/tests/test_be14_threat_simulation_e0_e5_statistics.py`
- `artifacts/evaluation/be14_candidate_suite/*`
- `docs/reviews/BE-14_AUDIT_AND_EVIDENCE.md`

## Task sequence

1. Confirm upstream dependencies (`BE-01..BE-13`) and unresolved P0 scientific blockers (`OQ-01` in `configs/views.scientific.yaml`, `OQ-02` in `configs/model.scientific.yaml`, and missing pre-trained poisoned LightGBM models in `models/`).
2. Freeze threat model, RQ1–RQ4 / H1–H4 matrix, dataset split hygiene, and clean-label trigger protocol in `evaluation/protocol.py`.
3. Implement AUROC, FPR, Recall, Locked Recall@FPR1%, Pre/Post-Defense ASR, Scoped Latency (`evaluation/metrics.py`), Wilson CI, and Paired Statistical Tests (`evaluation/statistics.py`).
4. Implement Blind Evaluation Protocol and custody separation in `evaluation/blind.py` and E0–E5 runner in `evaluation/runner.py`.
5. Add 36 comprehensive unit, statistical, security, adversarial audit, and artifact verification tests in `backend/tests/test_be14_threat_simulation_e0_e5_statistics.py`.
6. Execute real Frozen Candidate E0–E5 runs on `datasets/ember2018/X_test.dat` + `ember_model_2018.txt`, record SHA-256 digests under `artifacts/evaluation/be14_candidate_suite/`, and update traceability/readiness docs.

## Acceptance
- AUROC/FPR/Recall/ASR tests: **PASS** (`TestScientificMetricsImplementation` in `test_be14_threat_simulation_e0_e5_statistics.py`).
- Wilson CI: **PASS** (`TestWilsonConfidenceInterval` verified against reference textbook values and BE-07 `wilson_score_interval`).
- Paired tests: **PASS** (`TestPairedStatisticalTests` covering sample-ID pairing, McNemar exact/chi2, paired & cluster bootstrap, correlated DeLong AUROC, and Holm-Bonferroni).
- Blind protocol: **PASS** (`TestBlindEvaluationProtocol` covering role separation, manifest/env/payload leakage blocking, SHA-256 prediction sealing, post-hoc threshold tuning rejection, and Jev AI blind-data blocking).
- Adversarial Audit & Edge Cases: **PASS** (`TestAdversarialAuditAndEdgeCases` covering M5 Semantic Plausibility definition, clean-label poisoning budget, conservative calibration quantile selection, cluster-aware DeLong/bootstrap, and universal E0–E5 artifact recomputation).

## Done definition

No silent TBDs, no undocumented schema/API changes, 36/36 BE-14 tests pass, all E0–E5 candidate artifacts and SHA-256 manifests are persisted and independently recomputable from `raw_predictions.jsonl`, and strict scientific blockers (`OQ-01`, `OQ-02`, `MISSING_POISONED_MODELS`) are explicitly enforced and documented.
