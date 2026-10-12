from __future__ import annotations

import pytest
from x_sentinel.fusion.config import load_fusion_config
from x_sentinel.fusion.decision import (
    DecisionPolicy,
    DecisionVerdict,
    ThresholdProvenance,
    decision_from_score,
)


class TestThresholdProvenanceModel:
    """Verification of ThresholdProvenance data model and completeness."""

    def test_threshold_provenance_full_instantiation(self) -> None:
        prov = ThresholdProvenance(
            threshold_id="TH-D1-FPR01-20261012",
            value=0.4689,
            mode="d1",
            source="artifacts/calibration/d1_calibration.json",
            version="1.0.0",
            config_hash="a" * 64,
            fpr_target=0.01,
            empirical_fpr=0.01,
            wilson_ci=(0.0054, 0.0183),
            artifact_hash="b" * 64,
        )
        assert prov.threshold_id == "TH-D1-FPR01-20261012"
        assert prov.value == 0.4689
        assert prov.mode == "d1"
        assert prov.fpr_target == 0.01
        assert prov.wilson_ci == (0.0054, 0.0183)
        assert prov.artifact_hash == "b" * 64

    def test_threshold_provenance_d0_budget(self) -> None:
        prov = ThresholdProvenance(
            threshold_id="TH-D0-BUDGET-20261012",
            value=0.50,
            mode="d0",
            source="configs/detector.yaml",
            version="1.0.0",
            config_hash="c" * 64,
        )
        assert prov.threshold_id == "TH-D0-BUDGET-20261012"
        assert prov.mode == "d0"
        assert prov.value == 0.50
        assert prov.artifact_hash is None


class TestThresholdValidationInDecisionPolicy:
    """Verification of strict threshold bounds and validation."""

    def test_decision_policy_accepts_valid_thresholds(self) -> None:
        policy = DecisionPolicy(alert_threshold=0.50, quarantine_threshold=0.85)
        assert policy.alert_threshold == 0.50
        assert policy.quarantine_threshold == 0.85

    def test_decision_policy_rejects_negative_alert_threshold(self) -> None:
        with pytest.raises(ValueError, match="alert_threshold must be in"):
            DecisionPolicy(alert_threshold=-0.05, quarantine_threshold=0.85)

    def test_decision_policy_rejects_excessive_alert_threshold(self) -> None:
        with pytest.raises(ValueError, match="alert_threshold must be in"):
            DecisionPolicy(alert_threshold=1.05, quarantine_threshold=0.85)

    def test_decision_policy_rejects_negative_quarantine_threshold(self) -> None:
        with pytest.raises(ValueError, match="quarantine_threshold must be in"):
            DecisionPolicy(alert_threshold=0.50, quarantine_threshold=-0.1)

    def test_decision_policy_rejects_quarantine_less_than_alert(self) -> None:
        with pytest.raises(ValueError, match="cannot be less than alert_threshold"):
            DecisionPolicy(alert_threshold=0.70, quarantine_threshold=0.60)

    def test_decision_policy_fails_closed_when_scientific_threshold_none(self) -> None:
        policy = DecisionPolicy(alert_threshold=None, quarantine_threshold=0.85, demo_mode=False)
        with pytest.raises(RuntimeError, match="scientific threshold unresolved"):
            policy.evaluate(0.60)


class TestThresholdProvenanceLinkageFromConfig:
    """Verification that thresholds trace back to versioned configuration."""

    def test_load_detector_yaml_threshold_provenance(self) -> None:
        cfg = load_fusion_config("configs/detector.yaml")
        assert cfg.calibration.mode in ("d0", "d1")
        assert 0.0 <= cfg.calibration.d0_threshold <= 1.0
        assert 0.0 <= cfg.calibration.quarantine_threshold <= 1.0
        assert cfg.calibration.quarantine_threshold >= cfg.calibration.d0_threshold

    def test_backward_compatible_decision_from_score(self) -> None:
        assert decision_from_score(0.60, threshold=0.50, demo_mode=False) == "ALERT"
        assert decision_from_score(0.40, threshold=0.50, demo_mode=False) == "PASS"
        assert decision_from_score(0.50, threshold=0.50, demo_mode=False) == "ALERT"
        assert decision_from_score(0.80, threshold=0.50, demo_mode=True) == "DEMO_ONLY"

        with pytest.raises(RuntimeError, match="scientific threshold unresolved"):
            decision_from_score(0.50, threshold=None, demo_mode=False)


class TestThresholdBoundaryBehavior:
    """Precise numerical verification at the exact threshold boundaries."""

    def test_alert_threshold_boundaries(self) -> None:
        policy = DecisionPolicy(alert_threshold=0.50, quarantine_threshold=0.85, demo_mode=False)

        # Strictly below: PASS
        res_below = policy.evaluate(0.4999999)
        assert res_below.decision == DecisionVerdict.PASS.value

        # Exactly at threshold: ALERT (closed lower bound)
        res_exact = policy.evaluate(0.5000000)
        assert res_exact.decision == DecisionVerdict.ALERT.value

        # Strictly above: ALERT
        res_above = policy.evaluate(0.5000001)
        assert res_above.decision == DecisionVerdict.ALERT.value

    def test_quarantine_threshold_boundaries(self) -> None:
        policy = DecisionPolicy(alert_threshold=0.50, quarantine_threshold=0.85, demo_mode=False)

        # Strictly below quarantine threshold: ALERT
        res_below_q = policy.evaluate(0.8499999)
        assert res_below_q.decision == DecisionVerdict.ALERT.value

        # Exactly at quarantine threshold: QUARANTINE
        res_exact_q = policy.evaluate(0.8500000)
        assert res_exact_q.decision == DecisionVerdict.QUARANTINE.value

        # Strictly above quarantine threshold: QUARANTINE
        res_above_q = policy.evaluate(0.8500001)
        assert res_above_q.decision == DecisionVerdict.QUARANTINE.value
