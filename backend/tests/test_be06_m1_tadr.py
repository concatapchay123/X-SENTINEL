from __future__ import annotations

import math

import pytest
from x_sentinel.detection.config import M1Config
from x_sentinel.detection.m1_tadr import M1TADRDetector, m1_tadr
from x_sentinel.domain import SignalResult


class TestM1TADRFormula:
    """Mathematical verification and golden formula tests for M1 TADR."""

    def test_basic_reference_calculation(self) -> None:
        # [1.0, 1.0, 2.0] -> max=2.0, sum=4.0 -> 0.5
        assert m1_tadr([1.0, 1.0, 2.0]) == 0.5

    def test_single_dominant_feature(self) -> None:
        # One large spike among zeros
        vec = [0.0] * 2380 + [100.0]
        assert m1_tadr(vec) == 1.0

    def test_uniform_distribution(self) -> None:
        # Uniform attribution across 10 features: 1/10 = 0.1
        vec = [2.0] * 10
        assert math.isclose(m1_tadr(vec), 0.1, rel_tol=1e-9)

    def test_negative_shap_values_take_absolute_value(self) -> None:
        # SHAP attributions can be negative; formula uses |s_i|
        assert m1_tadr([-1.0, -1.0, -2.0]) == 0.5
        assert m1_tadr([3.0, -1.0, 0.0]) == 0.75

    def test_scale_invariance(self) -> None:
        # TADR(c * S) == TADR(S) for any positive scalar c
        base = [0.5, -1.5, 3.0, 0.0]
        expected = m1_tadr(base)
        for scale in [0.001, 10.0, 1000.0]:
            scaled = [v * scale for v in base]
            assert math.isclose(m1_tadr(scaled), expected, rel_tol=1e-9)

    def test_canonical_2381_vector_bounds(self) -> None:
        vec = [0.01 * (i % 7) for i in range(2381)]
        res = m1_tadr(vec)
        assert isinstance(res, float)
        assert 0.0 <= res <= 1.0

    def test_zero_vector_zero_denominator(self) -> None:
        # Total <= eps must cleanly return 0.0 without division by zero
        assert m1_tadr([0.0] * 2381) == 0.0
        assert m1_tadr([1e-13, -1e-13], eps=1e-12) == 0.0

    def test_determinism_repeated_execution(self) -> None:
        vec = [float(i) for i in range(2381)]
        res1 = m1_tadr(vec)
        res2 = m1_tadr(vec)
        assert res1 == res2


class TestM1TADRNegativeCases:
    """Negative input validation and error handling for M1 TADR."""

    def test_rejects_empty_input(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            m1_tadr([])

    def test_rejects_nan_value(self) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            m1_tadr([1.0, float("nan"), 2.0])

    def test_rejects_positive_infinity(self) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            m1_tadr([1.0, float("inf"), 2.0])

    def test_rejects_negative_infinity(self) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            m1_tadr([1.0, float("-inf"), 2.0])

    def test_rejects_string_element(self) -> None:
        with pytest.raises(TypeError, match="non-numeric"):
            m1_tadr([1.0, "spike", 2.0])  # type: ignore

    def test_rejects_none_element(self) -> None:
        with pytest.raises(TypeError, match="non-numeric"):
            m1_tadr([1.0, None, 2.0])  # type: ignore

    def test_rejects_boolean_element(self) -> None:
        # Booleans are subclasses of int in Python; must be explicitly rejected
        with pytest.raises(TypeError, match="non-numeric"):
            m1_tadr([1.0, True, 2.0])  # type: ignore

    def test_rejects_scalar_input(self) -> None:
        with pytest.raises(TypeError, match="sequence"):
            m1_tadr(42.0)  # type: ignore


class TestM1TADRDetectorClass:
    """Contract verification for M1TADRDetector class."""

    def test_detector_default_initialization(self) -> None:
        detector = M1TADRDetector()
        assert detector.name == "m1"
        assert detector.config.formula == "tadr"
        assert detector.config.enabled is True

    def test_detector_detect_output_contract(self) -> None:
        detector = M1TADRDetector()
        shap = [0.0] * 2380 + [5.0]
        result = detector.detect(shap)

        assert isinstance(result, SignalResult)
        assert result.name == "m1"
        assert result.score == 1.0
        assert result.diagnostics["formula"] == "tadr"
        assert result.diagnostics["top_feature_index"] == 2380
        assert result.diagnostics["top_feature_abs_shap"] == 5.0
        assert result.diagnostics["total_abs_shap"] == 5.0
        assert result.diagnostics["feature_count"] == 2381

    def test_detector_score_convenience_method(self) -> None:
        detector = M1TADRDetector()
        assert detector.score([1.0, 1.0, 2.0]) == 0.5

    def test_detector_disabled_returns_zero(self) -> None:
        cfg = M1Config(enabled=False)
        detector = M1TADRDetector(cfg)
        result = detector.detect([1.0, 2.0, 3.0])
        assert result.score == 0.0
        assert result.diagnostics["status"] == "DISABLED"

    def test_detector_dict_config_initialization(self) -> None:
        detector = M1TADRDetector({"enabled": True, "formula": "tadr", "eps": 1e-10})
        assert detector.config.eps == 1e-10
