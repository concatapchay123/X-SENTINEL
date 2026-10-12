from __future__ import annotations

import math
import pytest
from x_sentinel.detection.config import M4Config
from x_sentinel.detection.m4_cross_view import (
    M4CrossViewDetector,
    behavioral_metadata_gap,
    full_vs_behavioral_gap,
    max_pairwise_difference,
    symmetric_cross_view_disagreement,
    view_std,
)
from x_sentinel.domain import SignalResult


class TestSymmetricCrossViewDisagreement:
    """Mathematical verification of the frozen canonical M4 strategy (ADR-005)."""

    def test_full_agreement_yields_zero_disagreement(self) -> None:
        assert symmetric_cross_view_disagreement([0.5, 0.5, 0.5]) == 0.0
        assert symmetric_cross_view_disagreement([0.0, 0.0, 0.0]) == 0.0
        assert symmetric_cross_view_disagreement([1.0, 1.0, 1.0]) == 0.0

    def test_maximum_divergence_yields_one(self) -> None:
        # [1.0, 0.0, 0.0] -> 0.5 * (|1-0| + |0-0| + |0-1|) = 0.5 * 2.0 = 1.0
        assert symmetric_cross_view_disagreement([1.0, 0.0, 0.0]) == 1.0
        assert symmetric_cross_view_disagreement([0.0, 1.0, 0.0]) == 1.0
        assert symmetric_cross_view_disagreement([0.0, 0.0, 1.0]) == 1.0

    def test_permutation_symmetry(self) -> None:
        # Permutation of views must not change symmetric disagreement
        cases = [
            [0.8, 0.3, 0.1],
            [0.3, 0.1, 0.8],
            [0.1, 0.8, 0.3],
            [0.8, 0.1, 0.3],
            [0.1, 0.3, 0.8],
            [0.3, 0.8, 0.1],
        ]
        expected = symmetric_cross_view_disagreement(cases[0])
        for c in cases[1:]:
            assert math.isclose(symmetric_cross_view_disagreement(c), expected, rel_tol=1e-9)

    def test_partial_divergence_calculation(self) -> None:
        # [0.8, 0.2, 0.2] -> 0.5 * (|0.8 - 0.2| + |0.2 - 0.2| + |0.2 - 0.8|) = 0.5 * (0.6 + 0 + 0.6) = 0.6
        score = symmetric_cross_view_disagreement([0.8, 0.2, 0.2])
        assert math.isclose(score, 0.6, rel_tol=1e-9)

    def test_dict_input_support(self) -> None:
        views = {"structural": 0.8, "behavioral": 0.2, "metadata": 0.2}
        assert math.isclose(symmetric_cross_view_disagreement(views), 0.6, rel_tol=1e-9)


class TestM4AblationStrategies:
    """Verification of historical variants preserved as ablation strategies (TASK-13-03)."""

    def test_view_std_strategy(self) -> None:
        # Equal views -> std = 0.0
        assert view_std([0.5, 0.5, 0.5]) == 0.0

        # [1.0, 0.0, 0.0] -> mean=1/3, var = (4/9 + 1/9 + 1/9)/3 = 6/27 = 2/9, std = sqrt(2)/3 approx 0.4714
        expected_std = math.sqrt(2.0 / 9.0)
        assert math.isclose(view_std([1.0, 0.0, 0.0]), expected_std, rel_tol=1e-5)

    def test_behavioral_metadata_gap_strategy(self) -> None:
        views = {"structural": 0.1, "behavioral": 0.9, "metadata": 0.2}
        gap = behavioral_metadata_gap(views)
        assert math.isclose(gap, 0.7, rel_tol=1e-9)

    def test_full_vs_behavioral_gap_strategy(self) -> None:
        gap = full_vs_behavioral_gap(full_score=0.85, behavioral_score=0.15)
        assert math.isclose(gap, 0.7, rel_tol=1e-9)

    def test_max_pairwise_difference_strategy(self) -> None:
        # [0.9, 0.5, 0.2] -> diffs: 0.4, 0.3, 0.7 -> max = 0.7
        assert math.isclose(max_pairwise_difference([0.9, 0.5, 0.2]), 0.7, rel_tol=1e-9)


class TestM4CrossViewNegativeCases:
    """Negative input validation and error handling for M4."""

    def test_rejects_wrong_length_sequence(self) -> None:
        with pytest.raises(ValueError, match="Expected 3 view signals"):
            symmetric_cross_view_disagreement([0.5, 0.5])

        with pytest.raises(ValueError, match="Expected 3 view signals"):
            symmetric_cross_view_disagreement([0.1, 0.2, 0.3, 0.4])

    def test_rejects_non_finite_values(self) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            symmetric_cross_view_disagreement([0.5, float("nan"), 0.5])
        with pytest.raises(ValueError, match="non-finite"):
            symmetric_cross_view_disagreement([0.5, float("inf"), 0.5])

    def test_full_vs_behavioral_missing_full_score_raises(self) -> None:
        detector = M4CrossViewDetector(M4Config(strategy="full_vs_behavioral_gap"))
        with pytest.raises(ValueError, match="full_score is required"):
            detector.detect([0.5, 0.5, 0.5], full_score=None)

    def test_invalid_strategy_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported M4 strategy"):
            M4Config(strategy="invalid_unapproved_strategy")


class TestM4CrossViewDetectorClass:
    """Contract verification for M4CrossViewDetector class."""

    def test_detector_canonical_default(self) -> None:
        detector = M4CrossViewDetector()
        assert detector.name == "m4"
        assert detector.config.strategy == "symmetric_disagreement"

        views = {"structural": 1.0, "behavioral": 0.0, "metadata": 0.0}
        res = detector.detect(views)

        assert isinstance(res, SignalResult)
        assert res.name == "m4"
        assert res.score == 1.0
        assert res.diagnostics["strategy"] == "symmetric_disagreement"
        assert res.diagnostics["is_canonical"] is True
        assert res.diagnostics["max_difference"] == 1.0

    def test_detector_ablation_switch(self) -> None:
        cfg = M4Config(strategy="view_std")
        detector = M4CrossViewDetector(cfg)
        res = detector.detect([1.0, 0.0, 0.0])
        assert res.diagnostics["strategy"] == "view_std"
        assert res.diagnostics["is_canonical"] is False
        assert math.isclose(res.score, math.sqrt(2.0 / 9.0), rel_tol=1e-5)

    def test_detector_score_convenience_method(self) -> None:
        detector = M4CrossViewDetector()
        score = detector.score([0.5, 0.5, 0.5])
        assert score == 0.0

    def test_detector_disabled_returns_zero(self) -> None:
        cfg = M4Config(enabled=False)
        detector = M4CrossViewDetector(cfg)
        res = detector.detect([1.0, 0.0, 0.0])
        assert res.score == 0.0
        assert res.diagnostics["status"] == "DISABLED"
