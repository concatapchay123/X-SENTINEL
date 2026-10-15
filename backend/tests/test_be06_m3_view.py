from __future__ import annotations

import math
from pathlib import Path

import pytest
from x_sentinel.data.views import load_view_map
from x_sentinel.detection.config import M3Config
from x_sentinel.detection.m3_view import (
    M3ViewDetector,
    m3_view_concentration,
    view_contributions,
    view_entropy,
)
from x_sentinel.domain import SignalResult


class TestViewContributionsFormula:
    """Mathematical verification of view contribution aggregation."""

    def test_basic_view_contribution_calculation(self) -> None:
        views = {
            "structural": [1.0, 1.0],
            "behavioral": [2.0],
            "metadata": [0.0],
        }
        res = view_contributions(views)
        assert math.isclose(res["structural"], 0.5, rel_tol=1e-9)
        assert math.isclose(res["behavioral"], 0.5, rel_tol=1e-9)
        assert math.isclose(res["metadata"], 0.0, rel_tol=1e-9)
        assert math.isclose(sum(res.values()), 1.0, rel_tol=1e-9)

    def test_negative_values_converted_to_absolute(self) -> None:
        views = {
            "structural": [-3.0],
            "behavioral": [1.0],
            "metadata": [0.0],
        }
        res = view_contributions(views)
        assert math.isclose(res["structural"], 0.75, rel_tol=1e-9)
        assert math.isclose(res["behavioral"], 0.25, rel_tol=1e-9)
        assert math.isclose(res["metadata"], 0.0, rel_tol=1e-9)

    def test_all_zero_contributions_clean_return(self) -> None:
        views = {
            "structural": [0.0, 0.0],
            "behavioral": [0.0],
            "metadata": [0.0],
        }
        res = view_contributions(views)
        assert res == {"structural": 0.0, "behavioral": 0.0, "metadata": 0.0}

    def test_single_monopolizing_view(self) -> None:
        views = {
            "structural": [10.0],
            "behavioral": [0.0],
            "metadata": [0.0],
        }
        res = view_contributions(views)
        assert res["structural"] == 1.0
        assert res["behavioral"] == 0.0
        assert res["metadata"] == 0.0


class TestViewConcentrationAndEntropy:
    """Mathematical verification of concentration and Shannon entropy across views."""

    def test_view_concentration_monopoly(self) -> None:
        contrib = {"structural": 1.0, "behavioral": 0.0, "metadata": 0.0}
        assert m3_view_concentration(contrib) == 1.0

    def test_view_concentration_uniform(self) -> None:
        contrib = {"structural": 1.0 / 3.0, "behavioral": 1.0 / 3.0, "metadata": 1.0 / 3.0}
        assert math.isclose(m3_view_concentration(contrib), 1.0 / 3.0, rel_tol=1e-9)

    def test_view_entropy_uniform_distribution(self) -> None:
        # 3 equal views -> H = log2(3) approx 1.58496 bits
        contrib = {"structural": 1.0 / 3.0, "behavioral": 1.0 / 3.0, "metadata": 1.0 / 3.0}
        h = view_entropy(contrib)
        expected = math.log2(3.0)
        assert math.isclose(h, expected, rel_tol=1e-5)

    def test_view_entropy_monopoly_distribution(self) -> None:
        # Single view 1.0 -> H = 0.0 bits
        contrib = {"structural": 1.0, "behavioral": 0.0, "metadata": 0.0}
        h = view_entropy(contrib)
        assert h == 0.0


class TestM3ViewNegativeCases:
    """Negative validation and error handling for M3."""

    def test_rejects_non_dict_view_contributions(self) -> None:
        with pytest.raises(TypeError, match="must be a dict"):
            view_contributions([1.0, 2.0])  # type: ignore

    def test_rejects_non_finite_in_view(self) -> None:
        views = {"structural": [1.0, float("nan")], "behavioral": [1.0]}
        with pytest.raises(ValueError, match="non-finite"):
            view_contributions(views)

    def test_rejects_non_numeric_in_view(self) -> None:
        views = {"structural": [1.0, "bad"], "behavioral": [1.0]}
        with pytest.raises(TypeError, match="non-numeric"):
            view_contributions(views)  # type: ignore

    def test_concentration_rejects_non_dict(self) -> None:
        with pytest.raises(TypeError, match="must be a dict"):
            m3_view_concentration([0.5, 0.5])  # type: ignore


class TestM3ViewDetectorClass:
    """Contract verification for M3ViewDetector class."""

    def test_detector_detect_with_dict_views(self) -> None:
        detector = M3ViewDetector()
        views = {
            "structural": [10.0],
            "behavioral": [0.0],
            "metadata": [0.0],
        }
        res = detector.detect(views)

        assert isinstance(res, SignalResult)
        assert res.name == "m3"
        assert res.score == 1.0
        assert res.diagnostics["dominant_view"] == "structural"
        assert res.diagnostics["contributions"]["structural"] == 1.0
        assert res.diagnostics["view_entropy"] == 0.0

    def test_detector_detect_with_flat_vector_and_view_map(self) -> None:
        view_map = load_view_map(Path("configs/views.demo.yaml"), allow_demo=True)
        detector = M3ViewDetector()

        # Place 10.0 in structural view (index 10)
        shap_vec = [0.0] * 2381
        shap_vec[10] = 10.0

        res = detector.detect(shap_vec, view_map=view_map)
        assert res.name == "m3"
        assert res.score == 1.0
        assert res.diagnostics["dominant_view"] == "structural"

    def test_detector_score_convenience_method(self) -> None:
        detector = M3ViewDetector()
        views = {"structural": [5.0], "behavioral": [5.0], "metadata": [0.0]}
        assert detector.score(views) == 0.5

    def test_detector_disabled_returns_zero(self) -> None:
        cfg = M3Config(enabled=False)
        detector = M3ViewDetector(cfg)
        res = detector.detect({"structural": [1.0]})
        assert res.score == 0.0
        assert res.diagnostics["status"] == "DISABLED"
