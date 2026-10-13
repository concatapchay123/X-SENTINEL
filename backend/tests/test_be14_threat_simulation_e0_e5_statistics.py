from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score
from x_sentinel.data.schema import FEATURE_COUNT
from x_sentinel.evaluation import (
    EXPERIMENT_DEFINITIONS,
    RQ_HYPOTHESIS_MATRIX,
    THREAT_MODEL_SPEC,
    TRIGGER_FAMILIES,
    ASRResult,
    AttackManifest,
    BlindCustodyGuard,
    BlindCustodyIntegrityError,
    BlindEvaluationReport,
    BlindEvaluator,
    BlindGroundTruthManifest,
    BlindLabelLeakageError,
    BlindPredictionPackage,
    BlindRolePermissionError,
    BlindSamplePrediction,
    DatasetSplitManifest,
    DemoDecisionRejectedError,
    DuplicateSampleIDError,
    EvaluationLeakageError,
    EvaluationRole,
    EvaluationRunner,
    EvaluationRunSpec,
    ExperimentBlockedError,
    ForbiddenEnvironmentExposureError,
    FPRResult,
    LatencySummary,
    LockedOperatingPointResult,
    ManifestAccessDeniedError,
    McNemarResult,
    MetricError,
    MultipleComparisonResult,
    PairedAUROCResult,
    PairedBootstrapResult,
    PostHocTuningForbiddenError,
    RecallResult,
    SingleClassPopulationError,
    SplitIntegrityError,
    SplitRole,
    TriggerSpec,
    WilsonCIResult,
    ZeroDenominatorError,
    ZeroEligibleSamplesError,
    align_paired_records,
    apply_vector_trigger,
    audit_dataset_splits,
    check_scientific_readiness,
    compute_asr,
    compute_auroc,
    compute_fpr,
    compute_latency_summary,
    compute_recall,
    compute_recall_at_locked_fpr,
    holm_bonferroni_correction,
    mcnemar_paired_test,
    paired_auroc_comparison,
    paired_bootstrap_test,
    recompute_metrics_from_raw,
    verify_clean_label_integrity,
    wilson_ci,
)
from x_sentinel.fusion.calibration import wilson_score_interval
from x_sentinel.jev_ai.guardrails import JevBlindDataBlocked, validate_context

# ===========================================================================
# 1. TASK 14.1–14.4: THREAT MODEL, RQ/H, DATASET SPLITS & ATTACK PROTOCOL
# ===========================================================================


class TestThreatModelAndProtocolFreeze:
    """Verifies Task 14.1, 14.2, 14.3, 14.4 scientific baseline and boundaries."""

    def test_threat_model_and_rq_hypothesis_matrix_complete(self) -> None:
        assert THREAT_MODEL_SPEC["input_domain"] == "ember_2381_static_vector"
        assert THREAT_MODEL_SPEC["feature_count"] == FEATURE_COUNT
        assert THREAT_MODEL_SPEC["clean_label_only"] is True
        assert THREAT_MODEL_SPEC["feature_vector_simulation_only"] is True
        assert THREAT_MODEL_SPEC["binary_pe_feasibility_proven"] is False
        assert THREAT_MODEL_SPEC["malware_execution_permitted"] is False
        assert set(THREAT_MODEL_SPEC["defender_modes"]) == {"D0", "D1"}

        assert set(RQ_HYPOTHESIS_MATRIX.keys()) == {"RQ1", "RQ2", "RQ3", "RQ4"}
        for _rq_id, entry in RQ_HYPOTHESIS_MATRIX.items():
            assert entry["hypothesis"].startswith("H")
            assert len(entry["metrics"]) >= 1
            assert len(entry["experiments"]) >= 1

        assert set(TRIGGER_FAMILIES.keys()) == {"T-concentrated", "T-spread", "T-cross"}
        assert TRIGGER_FAMILIES["T-concentrated"]["views"] == ["metadata"]
        assert TRIGGER_FAMILIES["T-spread"]["views"] == ["behavioral"]
        assert set(TRIGGER_FAMILIES["T-cross"]["views"]) == {
            "structural",
            "behavioral",
            "metadata",
        }

        assert set(EXPERIMENT_DEFINITIONS.keys()) == {"E0", "E1", "E2", "E3", "E4", "E5"}

    def test_dataset_split_integrity_detects_leakage_and_duplicates(self) -> None:
        fit_split = DatasetSplitManifest(
            dataset_name="ember2018",
            dataset_version="2018-v2",
            role=SplitRole.FIT,
            sample_ids=("s_001", "s_002", "s_003", "s_004"),
            labels=(0, 0, 1, 1),
            feature_count=FEATURE_COUNT,
            seed=42,
        )
        cal_split = DatasetSplitManifest(
            dataset_name="ember2018",
            dataset_version="2018-v2",
            role=SplitRole.D1_CALIBRATION,
            sample_ids=("cal_001", "cal_002", "cal_003", "cal_004"),
            labels=(0, 0, 0, 0),
            feature_count=FEATURE_COUNT,
            seed=42,
        )
        eval_split = DatasetSplitManifest(
            dataset_name="ember2018",
            dataset_version="2018-v2",
            role=SplitRole.FINAL_BLIND_EVALUATION,
            sample_ids=("ev_001", "ev_002", "ev_003", "ev_004"),
            labels=(0, 0, 1, 1),
            feature_count=FEATURE_COUNT,
            seed=42,
        )

        report = audit_dataset_splits([fit_split, cal_split, eval_split])
        assert report["passed"] is True
        assert report["leakage_detected"] is False
        assert len(report["manifest_hashes"]) == 3

        # Inject train/eval sample ID leakage
        leaked_eval = DatasetSplitManifest(
            dataset_name="ember2018",
            dataset_version="2018-v2",
            role=SplitRole.FINAL_BLIND_EVALUATION,
            sample_ids=("s_002", "ev_002", "ev_003", "ev_004"),
            labels=(0, 0, 1, 1),
            feature_count=FEATURE_COUNT,
            seed=42,
        )
        with pytest.raises(SplitIntegrityError, match="Sample ID leakage"):
            audit_dataset_splits([fit_split, cal_split, leaked_eval])

        # Inject calibration/eval leakage
        leaked_cal_eval = DatasetSplitManifest(
            dataset_name="ember2018",
            dataset_version="2018-v2",
            role=SplitRole.FINAL_BLIND_EVALUATION,
            sample_ids=("cal_001", "ev_002", "ev_003", "ev_004"),
            labels=(0, 0, 1, 1),
            feature_count=FEATURE_COUNT,
            seed=42,
        )
        with pytest.raises(SplitIntegrityError, match="Sample ID leakage"):
            audit_dataset_splits([fit_split, cal_split, leaked_cal_eval])

        # Calibration split must not contain malware labels (label=1)
        bad_cal = DatasetSplitManifest(
            dataset_name="ember2018",
            dataset_version="2018-v2",
            role=SplitRole.D1_CALIBRATION,
            sample_ids=("cal_10", "cal_11"),
            labels=(0, 1),
            feature_count=FEATURE_COUNT,
            seed=42,
        )
        with pytest.raises(
            SplitIntegrityError, match="D1_CALIBRATION split must contain only benign"
        ):
            audit_dataset_splits([fit_split, bad_cal, eval_split])

    def test_dataset_split_detects_repeated_ids_across_seeds(self) -> None:
        eval_seed42 = DatasetSplitManifest(
            dataset_name="ember2018",
            dataset_version="2018-v2",
            role=SplitRole.FINAL_BLIND_EVALUATION,
            sample_ids=("ev_001", "ev_002", "ev_003"),
            labels=(0, 1, 1),
            feature_count=FEATURE_COUNT,
            seed=42,
        )
        eval_seed99 = DatasetSplitManifest(
            dataset_name="ember2018",
            dataset_version="2018-v2",
            role=SplitRole.FINAL_BLIND_EVALUATION,
            sample_ids=("ev_001", "ev_002", "ev_004"),
            labels=(0, 1, 0),
            feature_count=FEATURE_COUNT,
            seed=99,
        )
        report = audit_dataset_splits([eval_seed42, eval_seed99], allow_multi_seed_same_role=True)
        assert report["passed"] is True
        assert report["repeated_ids_across_seeds"] == ["ev_001", "ev_002"]
        assert report["requires_clustered_inference"] is True

    def test_clean_label_integrity_and_vector_trigger_application(self) -> None:
        trigger = TriggerSpec(
            family="T-concentrated",
            feature_indices=(1600, 1601, 1602, 1603),
            feature_values=(0.75, 0.80, 0.65, 0.90),
            modifiable_views=("metadata",),
        )
        manifest = AttackManifest(
            manifest_id="atk-t-conc-001",
            trigger=trigger,
            poison_rate=0.01,
            total_train_samples=1000,
            poisoned_sample_ids=tuple(f"p_{i}" for i in range(10)),
            original_labels=tuple(0 for _ in range(10)),
            poisoned_labels=tuple(0 for _ in range(10)),
            seed=42,
            target_label=0,
        )
        assert verify_clean_label_integrity(manifest) is True

        # Reject label flipping in clean-label backdoor protocol
        flipped_manifest = AttackManifest(
            manifest_id="atk-flipped",
            trigger=trigger,
            poison_rate=0.01,
            total_train_samples=1000,
            poisoned_sample_ids=tuple(f"p_{i}" for i in range(10)),
            original_labels=tuple(1 for _ in range(10)),
            poisoned_labels=tuple(0 for _ in range(10)),
            seed=42,
            target_label=0,
        )
        with pytest.raises(ValueError, match="Clean-label violation: labels were flipped"):
            verify_clean_label_integrity(flipped_manifest)

        # Apply vector-level trigger safely without mutating original vector
        base_vec = [0.1] * FEATURE_COUNT
        triggered_vec = apply_vector_trigger(base_vec, trigger)
        assert base_vec[1600] == 0.1
        assert triggered_vec[1600] == 0.75
        assert triggered_vec[1601] == 0.80
        assert len(triggered_vec) == FEATURE_COUNT


# ===========================================================================
# 2. TASK 14.11: AUROC / FPR / RECALL / ASR METRICS TESTS (ACCEPTANCE #1)
# ===========================================================================


class TestScientificMetricsImplementation:
    """Verifies Task 14.11: AUROC, FPR, Recall, Recall@FPR1%, ASR, Post-defense ASR."""

    def test_auroc_hand_computed_and_sklearn_equivalence(self) -> None:
        # 4 benign (0) with scores [0.1, 0.2, 0.3, 0.4]
        # 4 malware/triggered (1) with scores [0.35, 0.6, 0.8, 0.9]
        # Pairs (pos, neg): 4 * 4 = 16 pairs.
        # pos=0.35 beats 0.1, 0.2, 0.3 (3 of 4), loses to 0.4 (1 of 4).
        # pos=0.6, 0.8, 0.9 beat all 4 (12 of 12).
        # Total concordant = 15 / 16 = 0.9375.
        labels = [0, 0, 0, 0, 1, 1, 1, 1]
        scores = [0.10, 0.20, 0.30, 0.40, 0.35, 0.60, 0.80, 0.90]
        auroc = compute_auroc(labels, scores)
        assert math.isclose(auroc, 15.0 / 16.0, abs_tol=1e-12)
        assert math.isclose(auroc, roc_auc_score(labels, scores), abs_tol=1e-12)

    def test_auroc_with_tied_scores_exact(self) -> None:
        # 2 negative [0.2, 0.5], 2 positive [0.5, 0.9]
        # Pairs: (0.5, 0.2)->1, (0.5, 0.5)->0.5, (0.9, 0.2)->1, (0.9, 0.5)->1 => 3.5 / 4 = 0.875
        labels = [0, 0, 1, 1]
        scores = [0.2, 0.5, 0.5, 0.9]
        auroc = compute_auroc(labels, scores)
        assert math.isclose(auroc, 0.875, abs_tol=1e-12)
        assert math.isclose(auroc, roc_auc_score(labels, scores), abs_tol=1e-12)

    def test_auroc_preserves_score_direction_without_post_hoc_flipping(self) -> None:
        # Worse-than-random detector scores must report AUROC < 0.5 honestly
        labels = [0, 0, 1, 1]
        scores = [0.9, 0.8, 0.1, 0.2]
        auroc = compute_auroc(labels, scores, higher_is_more_suspicious=True)
        assert math.isclose(auroc, 0.0, abs_tol=1e-12)

        # Only when protocol explicitly defines lower_is_more_suspicious
        auroc_inv = compute_auroc(labels, scores, higher_is_more_suspicious=False)
        assert math.isclose(auroc_inv, 1.0, abs_tol=1e-12)

    def test_auroc_rejects_single_class_and_invalid_inputs(self) -> None:
        with pytest.raises(SingleClassPopulationError, match="both positive and negative"):
            compute_auroc([0, 0, 0], [0.1, 0.2, 0.3])
        with pytest.raises(SingleClassPopulationError, match="both positive and negative"):
            compute_auroc([1, 1, 1], [0.1, 0.2, 0.3])
        with pytest.raises(MetricError, match="empty"):
            compute_auroc([], [])
        with pytest.raises(MetricError, match="length mismatch"):
            compute_auroc([0, 1], [0.1])
        with pytest.raises(MetricError, match="binary label"):
            compute_auroc([0, 2], [0.1, 0.8])
        with pytest.raises(MetricError, match="boolean"):
            compute_auroc([False, True], [0.1, 0.8])  # type: ignore[list-item]
        with pytest.raises(MetricError, match="finite"):
            compute_auroc([0, 1], [0.1, float("nan")])
        with pytest.raises(DuplicateSampleIDError, match="Duplicate sample_id"):
            compute_auroc([0, 1], [0.2, 0.8], sample_ids=["id_1", "id_1"])

    def test_fpr_computation_threshold_equality_and_decisions(self) -> None:
        # 5 benign samples (label=0), 2 malware samples (label=1)
        # FPR must only use the 5 benign samples as denominator!
        labels = [0, 0, 0, 0, 0, 1, 1]
        scores = [0.10, 0.20, 0.50, 0.60, 0.30, 0.90, 0.95]

        # Inclusive threshold >= 0.50: 0.50 and 0.60 are FP -> 2 / 5 = 0.40
        res_inc = compute_fpr(labels, scores, threshold=0.50, inclusive=True)
        assert isinstance(res_inc, FPRResult)
        assert res_inc.fp == 2
        assert res_inc.tn == 3
        assert res_inc.benign_total == 5
        assert math.isclose(res_inc.fpr, 0.40, abs_tol=1e-12)
        assert math.isclose(res_inc.fpr_percent, 40.0, abs_tol=1e-12)

        # Strict threshold > 0.50: only 0.60 is FP -> 1 / 5 = 0.20
        res_strict = compute_fpr(labels, scores, threshold=0.50, inclusive=False)
        assert res_strict.fp == 1
        assert res_strict.tn == 4
        assert math.isclose(res_strict.fpr, 0.20, abs_tol=1e-12)

        # Canonical decisions
        decisions = ["PASS", "PASS", "ALERT", "QUARANTINE", "PASS", "ALERT", "QUARANTINE"]
        res_dec = compute_fpr(labels, decisions)
        assert res_dec.fp == 2
        assert res_dec.benign_total == 5
        assert math.isclose(res_dec.fpr, 0.40, abs_tol=1e-12)

        # Reject DEMO_ONLY decision in scientific evaluation
        with pytest.raises(DemoDecisionRejectedError, match="DEMO_ONLY"):
            compute_fpr([0, 0], ["PASS", "DEMO_ONLY"])

        # Reject zero benign denominator
        with pytest.raises(ZeroDenominatorError, match="benign"):
            compute_fpr([1, 1], [0.2, 0.8], threshold=0.5)

    def test_recall_variants_and_locked_recall_at_fpr1(self) -> None:
        labels = [0, 0, 1, 1, 1, 1]
        scores = [0.1, 0.2, 0.6, 0.7, 0.4, 0.9]
        # Eligible mask: only last 3 malware samples are successful eligible attacks
        eligible_mask = [False, False, False, True, True, True]

        # Recall on all triggered malware (4 samples: 0.6, 0.7, 0.4, 0.9 >= 0.5 -> 3/4 = 0.75)
        rec_all = compute_recall(labels, scores, threshold=0.50, recall_kind="triggered_malware")
        assert isinstance(rec_all, RecallResult)
        assert rec_all.tp == 3
        assert rec_all.fn == 1
        assert rec_all.positive_total == 4
        assert math.isclose(rec_all.recall, 0.75, abs_tol=1e-12)

        # Recall on successful eligible attacks (3 samples: 0.7, 0.4, 0.9 >= 0.5 -> 2/3)
        rec_elig = compute_recall(
            labels,
            scores,
            threshold=0.50,
            eligible_mask=eligible_mask,
            recall_kind="successful_eligible_attack",
        )
        assert rec_elig.tp == 2
        assert rec_elig.fn == 1
        assert rec_elig.positive_total == 3
        assert math.isclose(rec_elig.recall, 2.0 / 3.0, abs_tol=1e-12)

        # Locked Recall@FPR1% from independent D1 calibration set
        cal_benign = [float(i) / 100.0 for i in range(100)]  # 0.00 .. 0.99
        eval_labels = [0] * 20 + [1] * 10
        eval_scores = [0.10] * 19 + [0.995] + [0.995] * 8 + [0.20] * 2
        locked = compute_recall_at_locked_fpr(
            cal_benign_scores=cal_benign,
            eval_labels=eval_labels,
            eval_scores=eval_scores,
            target_fpr=0.01,
            cal_sample_ids=[f"cal_{i}" for i in range(100)],
            eval_sample_ids=[f"eval_{i}" for i in range(30)],
        )
        assert isinstance(locked, LockedOperatingPointResult)
        assert math.isclose(locked.locked_threshold, 0.99, abs_tol=1e-12)
        assert math.isclose(locked.recall.recall, 0.80, abs_tol=1e-12)
        assert math.isclose(locked.eval_fpr.fpr, 1.0 / 20.0, abs_tol=1e-12)

        # Reject overlap between calibration and evaluation sample IDs
        with pytest.raises(
            EvaluationLeakageError, match="Calibration and evaluation sample IDs overlap"
        ):
            compute_recall_at_locked_fpr(
                cal_benign_scores=cal_benign,
                eval_labels=eval_labels,
                eval_scores=eval_scores,
                target_fpr=0.01,
                cal_sample_ids=[f"cal_{i}" for i in range(100)],
                eval_sample_ids=["cal_0"] + [f"eval_{i}" for i in range(1, 30)],
            )

    def test_asr_and_post_defense_asr_denominators_and_controls(self) -> None:
        # 6 samples:
        # s0: benign (is_malware=0) -> excluded from eligible malware set E
        # s1: malware (is_malware=1), clean_score=0.20 (<0.5) -> misclassified by clean model,
        #     so excluded from eligible malware set E!
        # s2..s5: 4 eligible malware samples (clean_score >= 0.5)
        is_malware = [0, 1, 1, 1, 1, 1]
        clean_scores = [0.05, 0.20, 0.92, 0.88, 0.75, 0.95]
        # On poisoned model with trigger:
        # s2->0.10 (evaded), s3->0.20 (evaded), s4->0.40 (evaded), s5->0.85 (failed attack)
        # So 3 of 4 eligible attacks succeed -> ASR = 3/4 = 0.75
        poisoned_trig_scores = [0.02, 0.15, 0.10, 0.20, 0.40, 0.85]
        # Clean model with trigger (control):
        # Only s4 drops below 0.5 on clean model (0.45) -> control evasion = 1/4 = 0.25
        # Poisoning-associated gain = 0.75 - 0.25 = 0.50
        clean_trig_scores = [0.04, 0.18, 0.80, 0.70, 0.45, 0.90]
        # Detector flags s2 ("ALERT") and s3 ("QUARANTINE"), misses s4 ("PASS")
        # So only s4 both succeeds as an attack AND evades detector -> Post-defense ASR = 1/4 = 0.25
        detector_decisions = ["PASS", "PASS", "ALERT", "QUARANTINE", "PASS", "ALERT"]

        res = compute_asr(
            is_malware=is_malware,
            clean_model_scores=clean_scores,
            poisoned_triggered_scores=poisoned_trig_scores,
            malware_threshold=0.50,
            clean_triggered_scores=clean_trig_scores,
            detector_decisions_or_scores=detector_decisions,
            sample_ids=["s0", "s1", "s2", "s3", "s4", "s5"],
        )
        assert isinstance(res, ASRResult)
        assert res.total_malware_count == 5
        assert res.eligible_count == 4
        assert res.successful_attack_count == 3
        assert math.isclose(res.asr, 0.75, abs_tol=1e-12)
        assert res.clean_trigger_evasion_count == 1
        assert math.isclose(res.clean_trigger_evasion_rate or 0.0, 0.25, abs_tol=1e-12)
        assert math.isclose(res.poisoning_associated_gain or 0.0, 0.50, abs_tol=1e-12)
        assert res.post_defense_undefeated_count == 1
        assert math.isclose(res.post_defense_asr or 0.0, 0.25, abs_tol=1e-12)

        # Zero eligible malware raises ZeroEligibleSamplesError
        with pytest.raises(ZeroEligibleSamplesError, match="Zero eligible malware"):
            compute_asr(
                is_malware=[0, 1, 1],
                clean_model_scores=[0.1, 0.2, 0.3],
                poisoned_triggered_scores=[0.1, 0.1, 0.1],
                malware_threshold=0.50,
            )

    def test_latency_summary_scopes_and_percentiles(self) -> None:
        durations = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        summary = compute_latency_summary(durations, scope="detector_only", warmup_count=3)
        assert isinstance(summary, LatencySummary)
        assert summary.count == 10
        assert summary.scope == "detector_only"
        assert summary.warmup_count == 3
        assert math.isclose(summary.mean_ms, 5.5, abs_tol=1e-9)
        assert math.isclose(summary.p50_ms, 5.5, abs_tol=1e-9)
        assert summary.p95_ms >= 9.0
        assert summary.p99_ms >= 9.5

        with pytest.raises(ValueError, match="Unsupported latency scope"):
            compute_latency_summary(durations, scope="unspecified_scope")
        with pytest.raises(ValueError, match="non-negative"):
            compute_latency_summary([1.0, -0.5], scope="detector_only")


# ===========================================================================
# 3. TASK 14.12: WILSON CONFIDENCE INTERVAL TESTS (ACCEPTANCE #2)
# ===========================================================================


class TestWilsonConfidenceInterval:
    """Verifies Task 14.12: Wilson score confidence interval mathematical & edge cases."""

    def test_wilson_ci_reference_and_be07_equivalence(self) -> None:
        # 10 / 1000 at 95% confidence
        res = wilson_ci(10, 1000, confidence=0.95)
        assert isinstance(res, WilsonCIResult)
        low_ref, high_ref = wilson_score_interval(10, 1000, confidence=0.95)
        assert math.isclose(res.p_hat, 0.01, abs_tol=1e-12)
        assert math.isclose(res.lower, low_ref, abs_tol=1e-12)
        assert math.isclose(res.upper, high_ref, abs_tol=1e-12)
        assert math.isclose(res.lower, 0.005440754445529249, abs_tol=1e-9)
        assert math.isclose(res.upper, 0.018309468870314774, abs_tol=1e-9)

    def test_wilson_ci_boundary_cases(self) -> None:
        # k = 0
        r0 = wilson_ci(0, 50, confidence=0.95)
        assert r0.lower == 0.0
        assert 0.05 < r0.upper < 0.08

        # k = n
        rn = wilson_ci(50, 50, confidence=0.95)
        assert 0.92 < rn.lower < 0.95
        assert rn.upper == 1.0

        # k = 1, small n = 5
        r1 = wilson_ci(1, 5, confidence=0.95)
        assert 0.0 < r1.lower < 0.20 < r1.upper < 1.0

        # large n = 100,000
        rlarge = wilson_ci(1000, 100_000, confidence=0.95)
        assert 0.0093 < rlarge.lower < 0.0100 < rlarge.upper < 0.0107

        # 90% and 99% confidence levels
        r90 = wilson_ci(10, 100, confidence=0.90)
        r99 = wilson_ci(10, 100, confidence=0.99)
        assert (r99.upper - r99.lower) > (r90.upper - r90.lower)

    def test_wilson_ci_invalid_inputs_rejected(self) -> None:
        with pytest.raises(ValueError, match="strictly positive integer"):
            wilson_ci(0, 0)
        with pytest.raises(ValueError, match="strictly positive integer"):
            wilson_ci(0, -5)
        with pytest.raises(ValueError, match="must be in"):
            wilson_ci(-1, 10)
        with pytest.raises(ValueError, match="must be in"):
            wilson_ci(11, 10)
        with pytest.raises(TypeError, match="integer"):
            wilson_ci(1.5, 10)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="integer"):
            wilson_ci(1, 10.5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="integer"):
            wilson_ci(True, 10)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="confidence"):
            wilson_ci(5, 10, confidence=0.0)
        with pytest.raises(ValueError, match="confidence"):
            wilson_ci(5, 10, confidence=1.0)
        with pytest.raises(ValueError, match="confidence"):
            wilson_ci(5, 10, confidence=float("nan"))


# ===========================================================================
# 4. TASK 14.13: PAIRED STATISTICAL TESTS (ACCEPTANCE #3)
# ===========================================================================


class TestPairedStatisticalTests:
    """Verifies Task 14.13: Sample-ID pairing, McNemar, Paired/Cluster Bootstrap, DeLong."""

    def test_align_paired_records_by_sample_id_not_row_order(self) -> None:
        rec_a = [
            {"sample_id": "s1", "score": 0.9, "label": 1},
            {"sample_id": "s2", "score": 0.1, "label": 0},
            {"sample_id": "s3", "score": 0.8, "label": 1},
        ]
        # Shuffled order in B
        rec_b = [
            {"sample_id": "s3", "score": 0.4, "label": 1},
            {"sample_id": "s1", "score": 0.7, "label": 1},
            {"sample_id": "s2", "score": 0.2, "label": 0},
        ]
        aligned = align_paired_records(rec_a, rec_b)
        assert [pair[0]["sample_id"] for pair in aligned] == ["s1", "s2", "s3"]
        assert [pair[1]["score"] for pair in aligned] == [0.7, 0.2, 0.4]

        # Missing matching sample ID must fail
        with pytest.raises(ValueError, match="Mismatched sample IDs"):
            align_paired_records(rec_a, rec_b[:2])

        # Duplicate sample ID must fail
        with pytest.raises(DuplicateSampleIDError, match="Duplicate"):
            align_paired_records(rec_a + [rec_a[0]], rec_b + [rec_b[0]])

    def test_mcnemar_paired_test_discordance_and_zero_discordant_edge_case(self) -> None:
        # 20 paired samples:
        # both=8, a_only=10, b_only=1, neither=1 -> sum=20
        outcomes_a = [1] * 8 + [1] * 10 + [0] * 1 + [0] * 1
        outcomes_b = [1] * 8 + [0] * 10 + [1] * 1 + [0] * 1
        ids = [f"s_{i}" for i in range(20)]

        res = mcnemar_paired_test(outcomes_a, outcomes_b, sample_ids=ids)
        assert isinstance(res, McNemarResult)
        assert res.both_positive == 8
        assert res.a_only == 10
        assert res.b_only == 1
        assert res.neither == 1
        assert res.total_pairs == 20
        assert res.p_value < 0.02

        # Zero discordant pairs (a_only == 0, b_only == 0)
        res_ident = mcnemar_paired_test([1, 0, 1, 0], [1, 0, 1, 0], sample_ids=["a", "b", "c", "d"])
        assert res_ident.a_only == 0
        assert res_ident.b_only == 0
        assert res_ident.statistic == 0.0
        assert res_ident.p_value == 1.0

    def test_paired_bootstrap_handles_repeated_ids_via_cluster_resampling(self) -> None:
        # 10 unique samples evaluated across 3 seeds = 30 observations
        unique_ids = [f"sample_{i}" for i in range(10)]
        cluster_ids = unique_ids * 3
        obs_ids = [f"seed_{s}_sample_{i}" for s in range(3) for i in range(10)]
        vals_a = [0.80 + 0.01 * i for _ in range(3) for i in range(10)]
        vals_b = [0.50 + 0.01 * i for _ in range(3) for i in range(10)]

        res = paired_bootstrap_test(
            values_a=vals_a,
            values_b=vals_b,
            sample_ids=obs_ids,
            cluster_ids=cluster_ids,
            n_boot=500,
            confidence=0.95,
            seed=42,
        )
        assert isinstance(res, PairedBootstrapResult)
        assert res.n_observations == 30
        assert res.n_clusters == 10
        assert res.is_clustered is True
        assert math.isclose(res.observed_diff, 0.30, abs_tol=1e-9)
        assert res.ci_low > 0.25
        assert res.ci_high < 0.35

        # Determinism check with identical seed
        res2 = paired_bootstrap_test(
            values_a=vals_a,
            values_b=vals_b,
            sample_ids=obs_ids,
            cluster_ids=cluster_ids,
            n_boot=500,
            confidence=0.95,
            seed=42,
        )
        assert res.ci_low == res2.ci_low
        assert res.ci_high == res2.ci_high
        assert res.p_value == res2.p_value

    def test_paired_auroc_delong_and_bootstrap_comparison(self) -> None:
        rng = np.random.default_rng(42)
        labels = [0] * 40 + [1] * 40
        ids = [f"id_{i}" for i in range(80)]
        # Detector A separates classes strongly; Detector B is weaker
        scores_a = np.concatenate(
            [rng.uniform(0.05, 0.45, 40), rng.uniform(0.55, 0.95, 40)]
        ).tolist()
        scores_b = np.concatenate(
            [rng.uniform(0.20, 0.70, 40), rng.uniform(0.30, 0.80, 40)]
        ).tolist()

        res_delong = paired_auroc_comparison(
            labels=labels,
            scores_a=scores_a,
            scores_b=scores_b,
            sample_ids=ids,
            method="delong",
            seed=42,
        )
        assert isinstance(res_delong, PairedAUROCResult)
        assert res_delong.auroc_a > res_delong.auroc_b
        assert math.isclose(
            res_delong.delta_auroc, res_delong.auroc_a - res_delong.auroc_b, abs_tol=1e-12
        )
        assert res_delong.p_value < 0.05
        assert res_delong.ci_low > 0.0

        res_boot = paired_auroc_comparison(
            labels=labels,
            scores_a=scores_a,
            scores_b=scores_b,
            sample_ids=ids,
            method="bootstrap",
            n_boot=400,
            seed=42,
        )
        assert math.isclose(res_boot.delta_auroc, res_delong.delta_auroc, abs_tol=1e-12)
        assert res_boot.ci_low > 0.0

    def test_holm_bonferroni_multiple_comparison_correction(self) -> None:
        res = holm_bonferroni_correction(
            p_values=[0.005, 0.020, 0.040, 0.200],
            alpha=0.05,
            hypothesis_ids=["H1", "H2", "H3", "H4"],
        )
        assert isinstance(res, MultipleComparisonResult)
        assert res.method == "holm-bonferroni"
        assert res.rejected["H1"] is True
        assert res.rejected["H4"] is False
        assert res.adjusted_p_values["H1"] == pytest.approx(0.020)


# ===========================================================================
# 5. TASK 14.14: BLIND EVALUATION PROTOCOL TESTS (ACCEPTANCE #4)
# ===========================================================================


class TestBlindEvaluationProtocol:
    """Verifies Task 14.14: Role separation, custody isolation, and negative security tests."""

    def test_defense_blocked_from_reading_manifest_or_blind_labels(self, tmp_path: Path) -> None:
        custody_dir = tmp_path / "blind_custody_vault"
        custody_dir.mkdir()
        manifest_file = custody_dir / "poison_manifest.json"
        manifest_file.write_text('{"secret": true}', encoding="utf-8")

        guard = BlindCustodyGuard(
            role=EvaluationRole.DEFENSE_DETECTOR,
            restricted_custody_paths=[custody_dir],
        )

        # Defense attempts to read restricted custody directory
        with pytest.raises(ManifestAccessDeniedError, match="restricted custody"):
            guard.assert_path_allowed(manifest_file)

        # Defense attempts to read file named *manifest* or *ground_truth* anywhere
        with pytest.raises(ManifestAccessDeniedError, match="Forbidden manifest/ground-truth"):
            guard.assert_path_allowed(tmp_path / "trigger_manifest.json")
        with pytest.raises(ManifestAccessDeniedError, match="Forbidden manifest/ground-truth"):
            guard.assert_path_allowed(tmp_path / "blind_ground_truth.jsonl")

        # Defense receives payload containing blind labels or hidden cohort metadata
        for bad_payload in [
            {"sample_id": "s1", "blind_label": 1},
            {"sample_id": "s1", "ground_truth": 0},
            {"sample_id": "s1", "trigger_manifest": "T-cross"},
            {"sample_id": "s1", "metadata": {"hidden_cohort": "confirmed_attack"}},
            {"sample_id": "s1", "eval_label": 1},
        ]:
            with pytest.raises(BlindLabelLeakageError):
                guard.assert_defense_input_clean(bad_payload)

    def test_defense_blocked_when_forbidden_env_vars_exposed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        guard = BlindCustodyGuard(role=EvaluationRole.DEFENSE_DETECTOR)
        monkeypatch.setenv("XS_BLIND_GROUND_TRUTH_PATH", "/vault/truth.json")
        with pytest.raises(ForbiddenEnvironmentExposureError, match="XS_BLIND_GROUND_TRUTH_PATH"):
            guard.assert_environment_clean()

    def test_blind_prediction_package_sealing_and_tamper_detection(self, tmp_path: Path) -> None:
        preds = (
            BlindSamplePrediction(
                sample_id="b_001",
                malware_score=0.05,
                signals={"m1": 0.05, "m2": 0.04, "m3": 0.10, "m4": 0.05, "m5": 0.0},
                fusion_score=0.048,
                decision="PASS",
                latency_ms=2.1,
            ),
            BlindSamplePrediction(
                sample_id="b_002",
                malware_score=0.95,
                signals={"m1": 0.85, "m2": 0.80, "m3": 0.90, "m4": 0.85, "m5": 0.60},
                fusion_score=0.800,
                decision="ALERT",
                latency_ms=2.4,
            ),
        )
        pkg = BlindPredictionPackage.create(
            run_id="blind-run-001",
            experiment_code="E2",
            config_hash="a" * 64,
            model_hash="b" * 64,
            view_map_hash="c" * 64,
            detector_config_hash="d" * 64,
            threshold_id="CALIB-D1-BENIGN-EMBER2018-v1",
            threshold_value=0.46885473178149056,
            seed=42,
            predictions=preds,
        )
        assert pkg.verify_integrity() is True

        pkg_path = tmp_path / "predictions_pkg.json"
        pkg.save(pkg_path)
        loaded_pkg = BlindPredictionPackage.load(pkg_path)
        assert loaded_pkg.package_sha256 == pkg.package_sha256

        # Tamper with a prediction score in saved package
        raw_data = json.loads(pkg_path.read_text(encoding="utf-8"))
        raw_data["predictions"][0]["fusion_score"] = 0.999
        pkg_path.write_text(json.dumps(raw_data), encoding="utf-8")
        with pytest.raises(BlindCustodyIntegrityError, match="checksum mismatch"):
            BlindPredictionPackage.load(pkg_path)

    def test_blind_evaluator_enforces_role_and_prevents_post_hoc_tuning(self) -> None:
        preds = (
            BlindSamplePrediction(
                sample_id="b_001",
                malware_score=0.05,
                signals={"m1": 0.05, "m2": 0.04, "m3": 0.10, "m4": 0.05, "m5": 0.0},
                fusion_score=0.10,
                decision="PASS",
                latency_ms=2.1,
            ),
            BlindSamplePrediction(
                sample_id="b_002",
                malware_score=0.08,
                signals={"m1": 0.06, "m2": 0.05, "m3": 0.12, "m4": 0.06, "m5": 0.0},
                fusion_score=0.12,
                decision="PASS",
                latency_ms=2.2,
            ),
            BlindSamplePrediction(
                sample_id="m_001",
                malware_score=0.15,
                signals={"m1": 0.85, "m2": 0.80, "m3": 0.90, "m4": 0.85, "m5": 0.60},
                fusion_score=0.80,
                decision="ALERT",
                latency_ms=2.4,
            ),
            BlindSamplePrediction(
                sample_id="m_002",
                malware_score=0.20,
                signals={"m1": 0.75, "m2": 0.70, "m3": 0.80, "m4": 0.75, "m5": 0.50},
                fusion_score=0.70,
                decision="ALERT",
                latency_ms=2.5,
            ),
        )
        pkg = BlindPredictionPackage.create(
            run_id="blind-run-002",
            experiment_code="E2",
            config_hash="a" * 64,
            model_hash="b" * 64,
            view_map_hash="c" * 64,
            detector_config_hash="d" * 64,
            threshold_id="CALIB-D1-BENIGN-EMBER2018-v1",
            threshold_value=0.46885473178149056,
            seed=42,
            predictions=preds,
        )
        truth = BlindGroundTruthManifest.create(
            manifest_id="truth-002",
            dataset_id="ember2018-blind-test",
            sample_ids=("b_001", "b_002", "m_001", "m_002"),
            labels=(0, 0, 1, 1),
            is_malware=(0, 0, 1, 1),
            clean_model_scores=(0.02, 0.03, 0.95, 0.91),
            poisoned_triggered_scores=(0.02, 0.03, 0.15, 0.20),
        )

        # Defense role cannot instantiate or run BlindEvaluator
        with pytest.raises(BlindRolePermissionError, match="EVALUATION_SCORING"):
            BlindEvaluator(role=EvaluationRole.DEFENSE_DETECTOR)

        evaluator = BlindEvaluator(role=EvaluationRole.EVALUATION_SCORING)
        report = evaluator.score_predictions(
            prediction_package=pkg,
            ground_truth=truth,
            expected_locked_threshold=0.46885473178149056,
        )
        assert isinstance(report, BlindEvaluationReport)
        assert math.isclose(report.auroc, 1.0, abs_tol=1e-12)
        assert math.isclose(report.fpr.fpr, 0.0, abs_tol=1e-12)
        assert math.isclose(report.recall.recall, 1.0, abs_tol=1e-12)
        assert report.asr is not None
        assert math.isclose(report.asr.asr, 1.0, abs_tol=1e-12)
        assert math.isclose(report.asr.post_defense_asr or 0.0, 0.0, abs_tol=1e-12)

        # Post-hoc threshold tuning attempt must fail closed!
        with pytest.raises(PostHocTuningForbiddenError, match="Post-hoc threshold tuning"):
            evaluator.score_predictions(
                prediction_package=pkg,
                ground_truth=truth,
                expected_locked_threshold=0.25,
            )

    def test_blind_data_never_forwarded_to_jev_ai_context(self) -> None:
        with pytest.raises(JevBlindDataBlocked):
            validate_context({"analysis_id": "a1", "blind_label": 1})
        with pytest.raises(JevBlindDataBlocked):
            validate_context({"analysis_id": "a1", "poison_manifest": "atk-1"})


# ===========================================================================
# 6. TASK 14.5–14.10 & 14.15–14.19: E0–E5 RUNNER & REPRODUCIBILITY TESTS
# ===========================================================================


class TestExperimentRunnerAndE0ToE5Suite:
    """Verifies E0–E5 execution, blockers, raw prediction persistence, and recomputation."""

    def test_scientific_readiness_identifies_oq01_oq02_blockers(self) -> None:
        readiness = check_scientific_readiness()
        assert readiness["strict_scientific_ready"] is False
        blocker_ids = {b["id"] for b in readiness["blockers"]}
        assert "OQ-01" in blocker_ids
        assert "OQ-02" in blocker_ids
        assert "MISSING_POISONED_MODELS" in blocker_ids

        runner = EvaluationRunner(output_root=Path("artifacts/evaluation_test"))
        spec = EvaluationRunSpec(
            run_id="strict-blocked-run",
            experiment="E2",
            config_hash="a" * 64,
            dataset_hash="b" * 64,
            seed=42,
        )
        with pytest.raises(ExperimentBlockedError, match="OQ-01"):
            runner.run(spec, require_strict_scientific_freeze=True)

    def test_e0_to_e5_end_to_end_execution_and_recomputation(self, tmp_path: Path) -> None:
        runner = EvaluationRunner(output_root=tmp_path / "eval_runs")

        # 1. E0: Detector score distributions (with partial detection when poisoned model absent)
        e0_partial = runner.run_e0_distributions(
            run_id="e0-partial-test",
            clean_benign_scores={"s_b1": 0.05, "s_b2": 0.08, "s_b3": 0.12, "s_b4": 0.04},
            clean_triggered_scores={"s_m1": 0.15, "s_m2": 0.18, "s_m3": 0.22, "s_m4": 0.11},
            poisoned_benign_scores=None,
            poisoned_triggered_scores=None,
            threshold=0.46885473178149056,
            seed=42,
            evidence_class="SYNTHETIC_TEST_FIXTURE",
        )
        assert e0_partial["status"] == "PARTIAL"
        assert set(e0_partial["missing_groups"]) == {
            "poisoned_model_benign",
            "poisoned_model_triggered",
        }

        # Full 4-group E0
        e0_full = runner.run_e0_distributions(
            run_id="e0-full-test",
            clean_benign_scores={"s_b1": 0.05, "s_b2": 0.08, "s_b3": 0.12, "s_b4": 0.04},
            clean_triggered_scores={"s_m1": 0.15, "s_m2": 0.18, "s_m3": 0.22, "s_m4": 0.11},
            poisoned_benign_scores={"s_b1": 0.06, "s_b2": 0.09, "s_b3": 0.11, "s_b4": 0.05},
            poisoned_triggered_scores={"s_m1": 0.72, "s_m2": 0.81, "s_m3": 0.68, "s_m4": 0.77},
            threshold=0.46885473178149056,
            seed=42,
            evidence_class="SYNTHETIC_TEST_FIXTURE",
        )
        assert e0_full["status"] == "COMPLETED"
        assert e0_full["missing_groups"] == []

        # 2. E1: Attack viability & ASR (including weak/unconfirmed attack retention)
        e1_res = runner.run_e1_attack_viability(
            run_id="e1-viability-test",
            sample_ids=["m1", "m2", "m3", "m4", "m5", "b1"],
            is_malware=[1, 1, 1, 1, 1, 0],
            clean_model_scores=[0.95, 0.90, 0.85, 0.80, 0.20, 0.05],  # 4 eligible malware
            poisoned_triggered_scores=[0.10, 0.20, 0.15, 0.75, 0.10, 0.04],  # 3/4 = 0.75 ASR
            clean_triggered_scores=[0.88, 0.82, 0.40, 0.78, 0.15, 0.04],  # 1/4 = 0.25 control
            trigger_family="T-concentrated",
            poison_rate=0.01,
            seed=42,
            evidence_class="SYNTHETIC_TEST_FIXTURE",
        )
        assert e1_res["metrics"]["eligible_count"] == 4
        assert e1_res["metrics"]["successful_attack_count"] == 3
        assert math.isclose(e1_res["metrics"]["asr"], 0.75, abs_tol=1e-12)
        assert e1_res["metrics"]["confirmed_viable"] is True
        assert e1_res["metrics"]["meets_production_target"] is False

        # Weak attack (ASR = 0.25 <= 0.50 gate) must be retained and marked unconfirmed
        e1_weak = runner.run_e1_attack_viability(
            run_id="e1-weak-test",
            sample_ids=["m1", "m2", "m3", "m4"],
            is_malware=[1, 1, 1, 1],
            clean_model_scores=[0.95, 0.90, 0.85, 0.80],
            poisoned_triggered_scores=[0.10, 0.80, 0.82, 0.75],  # 1/4 = 0.25 ASR
            clean_triggered_scores=[0.90, 0.85, 0.80, 0.78],
            trigger_family="T-spread",
            poison_rate=0.005,
            seed=42,
            evidence_class="SYNTHETIC_TEST_FIXTURE",
        )
        assert math.isclose(e1_weak["metrics"]["asr"], 0.25, abs_tol=1e-12)
        assert e1_weak["metrics"]["confirmed_viable"] is False

        # 3. E2, E3, E4, E5 and independent recomputation from raw predictions
        sample_records = [
            {
                "sample_id": f"ben_{i}",
                "label": 0,
                "is_malware": 0,
                "clean_model_score": 0.02,
                "poisoned_triggered_score": 0.02,
                "signals": {
                    "m1": 0.05 + 0.01 * (i % 3),
                    "m2": 0.04 + 0.01 * (i % 3),
                    "m3": 0.12 + 0.01 * (i % 3),
                    "m4": 0.06 + 0.01 * (i % 3),
                    "m5": 0.00,
                },
                "fusion_reduced_score": 0.0675 + 0.01 * (i % 3),
                "fusion_full_score": 0.054 + 0.008 * (i % 3),
                "latency_ms": {
                    "detector_only": 1.5 + 0.1 * (i % 4),
                    "end_to_end": 3.0 + 0.1 * (i % 4),
                },
            }
            for i in range(10)
        ] + [
            {
                "sample_id": f"trig_{i}",
                "label": 1,
                "is_malware": 1,
                "clean_model_score": 0.92,
                "poisoned_triggered_score": 0.15 if i < 8 else 0.85,
                "signals": {
                    "m1": 0.55 if i % 2 == 0 else 0.30,
                    "m2": 0.52 if i % 3 == 0 else 0.28,
                    "m3": 0.65,
                    "m4": 0.70 if i < 7 else 0.35,
                    "m5": 0.80 if i < 9 else 0.20,
                },
                "fusion_reduced_score": 0.58 if i < 7 else 0.38,
                "fusion_full_score": 0.64 if i < 9 else 0.35,
                "latency_ms": {
                    "detector_only": 1.8 + 0.1 * (i % 4),
                    "end_to_end": 3.4 + 0.1 * (i % 4),
                },
            }
            for i in range(10)
        ]

        e2_res = runner.run_e2_detector_comparison(
            run_id="e2-comp-test",
            records=sample_records,
            locked_threshold=0.46885473178149056,
            threshold_id="CALIB-D1-BENIGN-EMBER2018-v1",
            seed=42,
            evidence_class="SYNTHETIC_TEST_FIXTURE",
        )
        assert "methods" in e2_res["metrics"]
        assert set(e2_res["metrics"]["methods"].keys()) == {
            "m1",
            "m2",
            "m3",
            "m4",
            "m5",
            "reduced_fusion",
            "full_fusion",
        }

        # Verify independent recomputation from saved raw_predictions.jsonl
        run_dir = tmp_path / "eval_runs" / "e2-comp-test"
        recomputed = recompute_metrics_from_raw(run_dir)
        assert recomputed["verified_match"] is True

        # Prevent silent overwrite of completed run
        with pytest.raises(FileExistsError, match="already completed"):
            runner.run_e2_detector_comparison(
                run_id="e2-comp-test",
                records=sample_records,
                locked_threshold=0.46885473178149056,
                threshold_id="CALIB-D1-BENIGN-EMBER2018-v1",
                seed=42,
                evidence_class="SYNTHETIC_TEST_FIXTURE",
            )

        # E3: Paired catch/miss analysis
        e3_res = runner.run_e3_paired_catch_miss(
            run_id="e3-catch-miss-test",
            records=sample_records,
            locked_threshold=0.46885473178149056,
            seed=42,
            evidence_class="SYNTHETIC_TEST_FIXTURE",
        )
        pair_m1_m4 = e3_res["metrics"]["pairs"]["m1_vs_m4"]
        assert (
            pair_m1_m4["both_detect"]
            + pair_m1_m4["a_only"]
            + pair_m1_m4["b_only"]
            + pair_m1_m4["neither"]
            == 10
        )

        # E4: Paired ablation study (Full vs Reduced Fusion)
        e4_res = runner.run_e4_ablation(
            run_id="e4-ablation-test",
            records=sample_records,
            locked_threshold=0.46885473178149056,
            seed=42,
            evidence_class="SYNTHETIC_TEST_FIXTURE",
        )
        assert "full_vs_reduced" in e4_res["metrics"]
        assert e4_res["metrics"]["full_vs_reduced"]["delta_recall"] >= 0.0

        # E5: Held-out benign FPR & Latency
        e5_res = runner.run_e5_fpr_latency(
            run_id="e5-fpr-latency-test",
            records=sample_records,
            locked_threshold=0.46885473178149056,
            seed=42,
            evidence_class="SYNTHETIC_TEST_FIXTURE",
        )
        assert math.isclose(e5_res["metrics"]["held_out_benign_fpr"]["fpr"], 0.0, abs_tol=1e-12)
        assert (
            e5_res["metrics"]["benign_subgroups"]["rare_benign"]["status"]
            == "BLOCKED_MISSING_SUBGROUP_LABELS"
        )
        assert "detector_only" in e5_res["metrics"]["latency_by_scope"]

    def test_evaluation_module_has_zero_jev_ai_runtime_dependency(self) -> None:
        eval_dir = Path("backend/src/x_sentinel/evaluation")
        for py_file in eval_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "JevAIClient" not in content
            assert "JevAIOrchestrator" not in content
            assert "JevAIService" not in content

    def test_frozen_candidate_suite_artifacts_and_checksums_verified(self) -> None:
        suite_dir = Path("artifacts/evaluation/be14_candidate_suite")
        summary_file = suite_dir / "suite_summary.json"
        assert summary_file.is_file(), "be14_candidate_suite/suite_summary.json must exist"

        summary = json.loads(summary_file.read_text(encoding="utf-8"))
        assert summary["evidence_class"] == "FROZEN_CANDIDATE_RUN"
        assert summary["strict_scientific_ready"] is False
        assert summary["sample_counts"]["benign"] == 25
        assert summary["sample_counts"]["malware_per_family"] == 25
        assert summary["sample_counts"]["total_pooled_records"] == 100

        # Verify independent metric recomputation from raw_predictions.jsonl across E2 runs
        for run_name in (
            "e2_pooled_seed42",
            "e2_t_concentrated_seed42",
            "e2_t_spread_seed42",
            "e2_t_cross_seed42",
        ):
            recomp = recompute_metrics_from_raw(suite_dir / run_name)
            assert recomp["verified_match"] is True

        # Verify sealed blind prediction package integrity
        sealed_pkg = BlindPredictionPackage.load(
            suite_dir / "blind_e2_pooled_seed42" / "sealed_predictions.json"
        )
        assert sealed_pkg.verify_integrity() is True
        assert len(sealed_pkg.predictions) == 100


class TestAdversarialAuditAndEdgeCases:
    """Adversarial review tests covering protocol, math, statistics, custody, and artifacts."""

    def test_rq3_defines_m5_as_semantic_plausibility_per_fr010(self) -> None:
        rq3_q = RQ_HYPOTHESIS_MATRIX["RQ3"]["question"]
        rq3_alt = RQ_HYPOTHESIS_MATRIX["RQ3"]["alternative_hypothesis"]
        assert "Semantic Plausibility" in rq3_q
        assert "Stability" not in rq3_q
        assert "K=8 perturbation" not in rq3_alt

    def test_attack_manifest_enforces_poison_budget_denominator_and_split_role(self) -> None:
        trigger = TriggerSpec(
            family="T-concentrated",
            feature_indices=(1600, 1601),
            feature_values=(0.80, 0.85),
            modifiable_views=("metadata",),
        )
        # Mismatched poison budget denominator: 50 / 1000 = 0.05 != declared poison_rate 0.01
        bad_budget_manifest = AttackManifest(
            manifest_id="atk-bad-budget",
            trigger=trigger,
            poison_rate=0.01,
            total_train_samples=1000,
            poisoned_sample_ids=tuple(f"p_{i}" for i in range(50)),
            original_labels=tuple(0 for _ in range(50)),
            poisoned_labels=tuple(0 for _ in range(50)),
            seed=42,
            target_label=0,
        )
        with pytest.raises(ValueError, match="Poisoning budget denominator mismatch"):
            verify_clean_label_integrity(bad_budget_manifest)

        # Forbidden split role for attack poisoning (e.g. FINAL_BLIND_EVALUATION)
        bad_role_manifest = AttackManifest(
            manifest_id="atk-bad-role",
            trigger=trigger,
            poison_rate=0.01,
            total_train_samples=1000,
            poisoned_sample_ids=tuple(f"p_{i}" for i in range(10)),
            original_labels=tuple(0 for _ in range(10)),
            poisoned_labels=tuple(0 for _ in range(10)),
            seed=42,
            target_label=0,
            source_split_role=SplitRole.FINAL_BLIND_EVALUATION,
        )
        with pytest.raises(ValueError, match="FIT"):
            verify_clean_label_integrity(bad_role_manifest)

        # TriggerSpec must reject modifiable_views inconsistent with trigger family
        with pytest.raises(ValueError, match="modifiable_views"):
            TriggerSpec(
                family="T-concentrated",
                feature_indices=(1600, 1601),
                feature_values=(0.80, 0.85),
                modifiable_views=("structural",),
            )

    def test_compute_recall_at_locked_fpr_matches_be07_d1_calibration_for_non_multiple_of_100(
        self,
    ) -> None:
        from x_sentinel.fusion.calibration import D1Calibration

        # N=105 benign calibration scores in [0, 1]:
        # allowed_fps = floor(0.01 * 105) = 1 -> rank index 104
        cal_scores = [float(i) / 200.0 for i in range(105)]
        d1_art = D1Calibration.fit(cal_scores, target_fpr=0.01)
        res = compute_recall_at_locked_fpr(
            cal_benign_scores=cal_scores,
            eval_labels=[0, 0, 1, 1],
            eval_scores=[0.10, 0.20, 0.60, 0.80],
            target_fpr=0.01,
        )
        assert math.isclose(res.locked_threshold, d1_art.threshold, abs_tol=1e-12)
        assert math.isclose(res.locked_threshold, 104.0 / 200.0, abs_tol=1e-12)

    def test_compute_recall_rejects_missing_eligible_mask_and_boolean_threshold(self) -> None:
        with pytest.raises(MetricError, match="eligible_mask is required"):
            compute_recall(
                [0, 1, 1],
                [0.1, 0.8, 0.9],
                threshold=0.5,
                recall_kind="successful_eligible_attack",
                eligible_mask=None,
            )
        with pytest.raises(MetricError, match="threshold"):
            compute_fpr([0, 1], [0.1, 0.8], threshold=True)  # type: ignore[arg-type]

        # Conventional malware recall is supported
        conv = compute_recall(
            [0, 1, 1],
            [0.1, 0.8, 0.3],
            threshold=0.5,
            recall_kind="conventional_malware",
        )
        assert math.isclose(conv.recall, 0.5, abs_tol=1e-12)

    def test_blind_custody_guard_blocks_standard_label_keys_and_ground_truth_validates_inputs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        guard = BlindCustodyGuard(role=EvaluationRole.DEFENSE_DETECTOR)
        for leaked_key in ("label", "labels", "is_malware", "y_true", "true_label"):
            with pytest.raises(BlindLabelLeakageError):
                guard.assert_defense_input_clean({"sample_id": "s1", leaked_key: 1})

        # BlindPredictionPackage.create must fail if forbidden blind env var is set
        monkeypatch.setenv("XS_BLIND_GROUND_TRUTH_PATH", "/vault/secret_truth.json")
        pred = BlindSamplePrediction(
            sample_id="s1",
            malware_score=0.1,
            signals={"m1": 0.1, "m2": 0.1, "m3": 0.1, "m4": 0.1, "m5": 0.0},
            fusion_score=0.08,
            decision="PASS",
            latency_ms=1.0,
        )
        with pytest.raises(ForbiddenEnvironmentExposureError):
            BlindPredictionPackage.create(
                run_id="r1",
                experiment_code="E2",
                config_hash="a" * 64,
                model_hash="b" * 64,
                view_map_hash="c" * 64,
                detector_config_hash="d" * 64,
                threshold_id="t1",
                threshold_value=0.5,
                seed=42,
                predictions=(pred,),
            )
        monkeypatch.delenv("XS_BLIND_GROUND_TRUTH_PATH")

        # BlindGroundTruthManifest must reject non-binary labels and mismatched score lengths
        with pytest.raises(ValueError, match="binary"):
            BlindGroundTruthManifest.create(
                manifest_id="m1",
                dataset_id="d1",
                sample_ids=["s1", "s2"],
                labels=[-1, 1],
                is_malware=[0, 1],
            )
        with pytest.raises(ValueError, match="length"):
            BlindGroundTruthManifest.create(
                manifest_id="m1",
                dataset_id="d1",
                sample_ids=["s1", "s2"],
                labels=[0, 1],
                is_malware=[0, 1],
                clean_model_scores=[0.1],
                poisoned_triggered_scores=[0.1, 0.2],
            )

    def test_e4_ablation_and_paired_auroc_enforce_cluster_inference_on_repeated_base_samples(
        self, tmp_path: Path
    ) -> None:
        runner = EvaluationRunner(output_root=tmp_path / "clustered_e4")
        # 5 benign samples + 5 base malware samples repeated across 3 trigger families (15 pos)
        records = [
            {
                "sample_id": f"ben_{i}",
                "base_sample_id": f"ben_{i}",
                "label": 0,
                "is_malware": 0,
                "signals": {"m1": 0.1, "m2": 0.1, "m3": 0.2, "m4": 0.15, "m5": 0.0},
                "fusion_reduced_score": 0.1375,
                "fusion_full_score": 0.11,
            }
            for i in range(5)
        ] + [
            {
                "sample_id": f"mal_{i}_{fam}",
                "base_sample_id": f"mal_{i}",
                "label": 1,
                "is_malware": 1,
                "signals": {
                    "m1": 0.30 + 0.02 * i,
                    "m2": 0.40,
                    "m3": 0.60,
                    "m4": 0.70 + 0.02 * i,
                    "m5": 0.80,
                },
                "fusion_reduced_score": 0.50 + 0.01 * i,
                "fusion_full_score": 0.56 + 0.01 * i,
            }
            for fam in ("t_conc", "t_spread", "t_cross")
            for i in range(5)
        ]
        e4_res = runner.run_e4_ablation(
            run_id="e4-cluster-test",
            records=records,
            locked_threshold=0.45,
            seed=42,
        )
        boot_info = e4_res["metrics"]["full_vs_reduced"]["paired_score_bootstrap"]
        assert boot_info["is_clustered"] is True
        assert boot_info["n_observations"] == 15
        assert boot_info["n_clusters"] == 5

    def test_recompute_metrics_and_artifact_integrity_across_all_e0_to_e5_runs(
        self, tmp_path: Path
    ) -> None:
        suite_dir = Path("artifacts/evaluation/be14_candidate_suite")
        for run_sub in (
            "e0_distributions_seed42",
            "e1_t_concentrated_seed42",
            "e2_pooled_seed42",
            "e3_paired_catch_miss_seed42",
            "e4_ablation_seed42",
            "e5_fpr_latency_seed42",
        ):
            recomp = recompute_metrics_from_raw(suite_dir / run_sub)
            assert recomp["verified_match"] is True
            assert recomp["checksum_verified"] is True

        # E0 in candidate suite must include M1/TADR score distributions per Task 14.5
        e0_metrics = json.loads(
            (suite_dir / "e0_distributions_seed42" / "metrics.json").read_text(encoding="utf-8")
        )
        assert "m1_tadr_groups" in e0_metrics
        assert (
            e0_metrics["m1_tadr_groups"]["clean_model_benign"]["status"] == "PRESENT"
        )
        assert (
            e0_metrics["m1_tadr_groups"]["clean_model_triggered"]["status"] == "PRESENT"
        )

        # E4 in candidate suite must report clustered bootstrap (25 base malware clusters, 75 obs)
        e4_metrics = json.loads(
            (suite_dir / "e4_ablation_seed42" / "metrics.json").read_text(encoding="utf-8")
        )
        assert (
            e4_metrics["full_vs_reduced"]["paired_score_bootstrap"]["is_clustered"] is True
        )
        assert e4_metrics["full_vs_reduced"]["paired_score_bootstrap"]["n_clusters"] == 25

        # E5 in candidate suite must have warmup_count > 0
        e5_metrics = json.loads(
            (suite_dir / "e5_fpr_latency_seed42" / "metrics.json").read_text(encoding="utf-8")
        )
        assert e5_metrics["latency_by_scope"]["detector_only"]["warmup_count"] > 0

        # Corrupted artifact checksum must fail verification
        corrupt_dir = tmp_path / "corrupt_run"
        corrupt_dir.mkdir()
        for fname in ("manifest.json", "metrics.json", "raw_predictions.jsonl", "checksums.sha256"):
            src = suite_dir / "e3_paired_catch_miss_seed42" / fname
            (corrupt_dir / fname).write_bytes(src.read_bytes())
        # Tamper with metrics.json in corrupt_dir
        bad_m = json.loads((corrupt_dir / "metrics.json").read_text(encoding="utf-8"))
        bad_m["pairs"]["m1_vs_m4"]["a_only"] = 999
        (corrupt_dir / "metrics.json").write_text(json.dumps(bad_m), encoding="utf-8")
        with pytest.raises(ValueError, match="checksum mismatch"):
            recompute_metrics_from_raw(corrupt_dir)

