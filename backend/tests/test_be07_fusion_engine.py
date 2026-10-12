from __future__ import annotations

import pytest
from x_sentinel.domain import SignalResult
from x_sentinel.fusion.config import (
    FusionConfig,
    FusionConfigError,
)
from x_sentinel.fusion.engine import (
    FusionEngine,
    InvalidSignalError,
    LogisticRegressionFusion,
    MaxSignalFusion,
    MissingSignalError,
    SignalDomainError,
    WeightedSumFusion,
    demo_fusion,
    validate_signals,
)


class TestSignalValidation:
    """Verification of signal input contract and bounds enforcement."""

    def test_valid_dict_input(self) -> None:
        raw = {"m1": 0.1, "m2": 0.2, "m3": 0.3, "m4": 0.4, "m5": 0.5}
        validated = validate_signals(raw)
        assert len(validated) == 5
        assert validated["m1"] == 0.1
        assert validated["m5"] == 0.5

    def test_case_insensitive_keys_and_whitespace(self) -> None:
        raw = {" M1 ": 0.1, "M2": 0.2, "m3": 0.3, "M4 ": 0.4, "m5": 0.5}
        validated = validate_signals(raw)
        assert set(validated.keys()) == {"m1", "m2", "m3", "m4", "m5"}
        assert validated["m1"] == 0.1

    def test_signal_result_objects_supported(self) -> None:
        raw = {
            "m1": SignalResult(name="m1", score=0.15),
            "m2": SignalResult(name="m2", score=0.25),
            "m3": SignalResult(name="m3", score=0.35),
            "m4": SignalResult(name="m4", score=0.45),
            "m5": SignalResult(name="m5", score=0.55),
        }
        validated = validate_signals(raw)
        assert validated["m1"] == 0.15
        assert validated["m5"] == 0.55

    def test_sequence_of_five_floats(self) -> None:
        raw = [0.1, 0.2, 0.3, 0.4, 0.5]
        validated = validate_signals(raw)
        assert validated["m1"] == 0.1
        assert validated["m5"] == 0.5

    def test_rejects_missing_signal(self) -> None:
        raw = {"m1": 0.1, "m2": 0.2, "m3": 0.3, "m4": 0.4}  # Missing m5
        with pytest.raises(MissingSignalError, match="signal 'm5' is missing"):
            validate_signals(raw)

    def test_rejects_sequence_wrong_length(self) -> None:
        with pytest.raises(MissingSignalError, match="Expected exactly 5 signals"):
            validate_signals([0.1, 0.2, 0.3, 0.4])

    def test_rejects_non_numeric_signal(self) -> None:
        raw = {"m1": "not_a_number", "m2": 0.2, "m3": 0.3, "m4": 0.4, "m5": 0.5}
        with pytest.raises(InvalidSignalError, match="cannot be converted to float"):
            validate_signals(raw)

    def test_rejects_nan_signal(self) -> None:
        raw = {"m1": float("nan"), "m2": 0.2, "m3": 0.3, "m4": 0.4, "m5": 0.5}
        with pytest.raises(InvalidSignalError, match="non-finite"):
            validate_signals(raw)

    def test_rejects_infinity_signal(self) -> None:
        raw = {"m1": float("inf"), "m2": 0.2, "m3": 0.3, "m4": 0.4, "m5": 0.5}
        with pytest.raises(InvalidSignalError, match="non-finite"):
            validate_signals(raw)

    def test_rejects_signal_below_zero(self) -> None:
        raw = {"m1": -0.001, "m2": 0.2, "m3": 0.3, "m4": 0.4, "m5": 0.5}
        with pytest.raises(SignalDomainError, match="violates domain"):
            validate_signals(raw)

    def test_rejects_signal_above_one(self) -> None:
        raw = {"m1": 1.001, "m2": 0.2, "m3": 0.3, "m4": 0.4, "m5": 0.5}
        with pytest.raises(SignalDomainError, match="violates domain"):
            validate_signals(raw)

    def test_rejects_invalid_input_type(self) -> None:
        with pytest.raises(TypeError, match="must be a Mapping or Sequence"):
            validate_signals(12345)  # type: ignore


class TestWeightedSumFusionStrategy:
    """Mathematical verification of WeightedSumFusion."""

    def test_equal_weights_calculation(self) -> None:
        weights = {"m1": 0.2, "m2": 0.2, "m3": 0.2, "m4": 0.2, "m5": 0.2}
        strategy = WeightedSumFusion(weights)
        signals = {"m1": 0.1, "m2": 0.2, "m3": 0.3, "m4": 0.4, "m5": 0.5}
        score = strategy.fuse(signals)
        expected = 0.2 * (0.1 + 0.2 + 0.3 + 0.4 + 0.5)  # 0.2 * 1.5 = 0.3
        assert abs(score - expected) < 1e-12

    def test_custom_weights_calculation(self) -> None:
        weights = {"m1": 0.4, "m2": 0.3, "m3": 0.1, "m4": 0.1, "m5": 0.1}
        strategy = WeightedSumFusion(weights)
        signals = {"m1": 1.0, "m2": 0.0, "m3": 0.0, "m4": 0.0, "m5": 0.0}
        score = strategy.fuse(signals)
        assert abs(score - 0.4) < 1e-12

    def test_mathematical_edge_cases(self) -> None:
        weights = {"m1": 0.2, "m2": 0.2, "m3": 0.2, "m4": 0.2, "m5": 0.2}
        strategy = WeightedSumFusion(weights)

        # All zeros -> 0.0
        assert strategy.fuse({"m1": 0.0, "m2": 0.0, "m3": 0.0, "m4": 0.0, "m5": 0.0}) == 0.0

        # All ones -> 1.0
        assert strategy.fuse({"m1": 1.0, "m2": 1.0, "m3": 1.0, "m4": 1.0, "m5": 1.0}) == 1.0

        # Equal signals c -> c
        c = 0.732
        assert abs(strategy.fuse({"m1": c, "m2": c, "m3": c, "m4": c, "m5": c}) - c) < 1e-12


class TestLogisticRegressionFusionStrategy:
    """Mathematical verification of LogisticRegressionFusion."""

    def test_logistic_regression_sigmoid_calculation(self) -> None:
        weights = {"m1": 1.0, "m2": 1.0, "m3": 1.0, "m4": 1.0, "m5": 1.0}
        bias = -2.5
        strategy = LogisticRegressionFusion(weights, bias=bias)
        # All signals 0.5 -> z = -2.5 + 5 * 0.5 = 0.0 -> sigma(0) = 0.5
        signals = {"m1": 0.5, "m2": 0.5, "m3": 0.5, "m4": 0.5, "m5": 0.5}
        score = strategy.fuse(signals)
        assert abs(score - 0.5) < 1e-12

    def test_logistic_regression_asymptotic_bounds(self) -> None:
        weights = {"m1": 10.0, "m2": 10.0, "m3": 10.0, "m4": 10.0, "m5": 10.0}
        strategy = LogisticRegressionFusion(weights, bias=0.0)
        score_high = strategy.fuse({"m1": 1.0, "m2": 1.0, "m3": 1.0, "m4": 1.0, "m5": 1.0})
        assert 0.999 < score_high <= 1.0


class TestMaxSignalFusionStrategy:
    """Mathematical verification of MaxSignalFusion."""

    def test_max_signal_returns_highest_signal(self) -> None:
        strategy = MaxSignalFusion()
        signals = {"m1": 0.1, "m2": 0.95, "m3": 0.4, "m4": 0.2, "m5": 0.3}
        assert strategy.fuse(signals) == 0.95


class TestFusionEngineAndConfigValidation:
    """Verification of configuration loading and FusionEngine execution."""

    def test_config_rejects_weights_not_summing_to_one(self) -> None:
        with pytest.raises(FusionConfigError, match="must sum to 1.0"):
            FusionConfig(
                strategy="weighted_sum",
                weights={"m1": 0.3, "m2": 0.3, "m3": 0.3, "m4": 0.3, "m5": 0.3},
            )

    def test_config_rejects_negative_weight(self) -> None:
        with pytest.raises(FusionConfigError, match="must be non-negative"):
            FusionConfig(
                strategy="weighted_sum",
                weights={"m1": 1.2, "m2": -0.2, "m3": 0.0, "m4": 0.0, "m5": 0.0},
            )

    def test_config_rejects_unsupported_strategy(self) -> None:
        with pytest.raises(FusionConfigError, match="Unsupported fusion strategy"):
            FusionConfig(strategy="random_forest_ensemble")

    def test_fusion_engine_evaluate_returns_result_with_metadata(self) -> None:
        engine = FusionEngine()
        signals = {"m1": 0.1, "m2": 0.2, "m3": 0.3, "m4": 0.4, "m5": 0.5}
        result = engine.evaluate(signals)

        assert abs(result.score - 0.3) < 1e-12
        assert result.strategy == "weighted_sum"
        assert result.version == "1.0.0"
        assert result.signals["m1"] == 0.1

    def test_fusion_determinism(self) -> None:
        engine = FusionEngine()
        signals = {"m1": 0.123456, "m2": 0.654321, "m3": 0.5, "m4": 0.75, "m5": 0.25}
        scores = [engine.score(signals) for _ in range(50)]
        assert len(set(scores)) == 1

    def test_legacy_demo_fusion_compatibility(self) -> None:
        assert abs(demo_fusion({"m1": 0.2, "m2": 0.4}) - 0.3) < 1e-12
        assert demo_fusion({}) == 0.0
