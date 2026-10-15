from __future__ import annotations

import math

import pytest
from x_sentinel.detection.config import M2Config
from x_sentinel.detection.m2_strip import M2StripDetector, binary_entropy, tabular_strip
from x_sentinel.domain import SignalResult


class TestBinaryEntropy:
    """Mathematical verification of binary Shannon entropy in bits."""

    def test_maximum_entropy_at_half(self) -> None:
        # H(0.5) = - 0.5*log2(0.5) - 0.5*log2(0.5) = 1.0 bit
        assert math.isclose(binary_entropy(0.5), 1.0, rel_tol=1e-9)

    def test_boundary_zero_and_one(self) -> None:
        # 0 * log2(0) == 0 by information theory limit convention
        assert binary_entropy(0.0) == 0.0
        assert binary_entropy(1.0) == 0.0

    def test_symmetry_property(self) -> None:
        # H(p) == H(1 - p)
        for p in [0.05, 0.1, 0.25, 0.33, 0.7, 0.95]:
            assert math.isclose(binary_entropy(p), binary_entropy(1.0 - p), rel_tol=1e-9)

    def test_entropy_bounds(self) -> None:
        for p_int in range(0, 101):
            p = p_int / 100.0
            h = binary_entropy(p)
            assert 0.0 <= h <= 1.0

    def test_rejects_non_finite_probability(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            binary_entropy(float("nan"))
        with pytest.raises(ValueError, match="finite"):
            binary_entropy(float("inf"))

    def test_rejects_non_numeric_type(self) -> None:
        with pytest.raises(TypeError, match="numeric"):
            binary_entropy("0.5")  # type: ignore
        with pytest.raises(TypeError, match="numeric"):
            binary_entropy(True)  # type: ignore


class TestTabularSTRIPLogic:
    """Verification of tabular perturbation and STRIP detection mechanics."""

    def test_trojan_invariant_prediction_yields_maximum_suspicion(self) -> None:
        # Strong backdoor: perturbed samples always predict target class 1.0
        # Entropy is 0.0 -> Inverted suspicion is 1.0
        vec = [1.0] * 2381
        pool = [[0.0] * 2381 for _ in range(10)]

        def trojan_model(_x: list[float]) -> float:
            return 1.0

        score, diag = tabular_strip(
            vector=vec,
            model_fn=trojan_model,
            benign_pool=pool,
            n_mix=16,
            alpha=0.2,
            invert_entropy=True,
        )
        assert score == 1.0
        assert diag["average_entropy"] == 0.0
        assert diag["n_mix"] == 16

    def test_clean_high_entropy_prediction_yields_minimum_suspicion(self) -> None:
        # Benign sample: perturbation causes maximum uncertainty (p=0.5, H=1.0)
        # Entropy is 1.0 -> Inverted suspicion is 0.0
        vec = [0.0] * 2381
        pool = [[1.0] * 2381 for _ in range(10)]

        def clean_uncertain_model(_x: list[float]) -> float:
            return 0.5

        score, diag = tabular_strip(
            vector=vec,
            model_fn=clean_uncertain_model,
            benign_pool=pool,
            n_mix=16,
            alpha=0.2,
            invert_entropy=True,
        )
        assert score == 0.0
        assert diag["average_entropy"] == 1.0

    def test_deterministic_sampling_with_fixed_seed(self) -> None:
        vec = [0.1 * i for i in range(10)]
        pool = [[float(i + j) for i in range(10)] for j in range(20)]

        def dummy_model(x: list[float]) -> float:
            return min(max(sum(x) / (len(x) * 10.0), 0.0), 1.0)

        score1, diag1 = tabular_strip(vec, dummy_model, pool, n_mix=8, alpha=0.2, sampling_seed=42)
        score2, diag2 = tabular_strip(vec, dummy_model, pool, n_mix=8, alpha=0.2, sampling_seed=42)

        assert score1 == score2
        assert diag1["average_entropy"] == diag2["average_entropy"]

    def test_raw_entropy_metric_when_not_inverted(self) -> None:
        vec = [0.0] * 10
        pool = [[0.0] * 10]

        def model_p(_x: list[float]) -> float:
            return 0.5

        score, diag = tabular_strip(vec, model_p, pool, n_mix=4, invert_entropy=False)
        assert score == 1.0  # Raw entropy
        assert diag["average_entropy"] == 1.0

    def test_convex_mixing_arithmetic(self) -> None:
        # Check that mixed vector actually receives (1 - alpha)*x + alpha*x_b
        vec = [10.0] * 5
        pool = [[0.0] * 5]
        captured_x: list[float] = []

        def capture_model(x: list[float]) -> float:
            nonlocal captured_x
            captured_x = list(x)
            return 0.5

        tabular_strip(vec, capture_model, pool, n_mix=1, alpha=0.2)
        # (1 - 0.2) * 10.0 + 0.2 * 0.0 = 8.0
        for v in captured_x:
            assert math.isclose(v, 8.0, rel_tol=1e-9)


class TestTabularSTRIPNegativeCases:
    """Negative validation and edge cases for M2 STRIP."""

    def test_rejects_empty_vector(self) -> None:
        with pytest.raises(ValueError, match="vector cannot be empty"):
            tabular_strip([], lambda x: 0.5, [[0.0]])

    def test_rejects_empty_pool(self) -> None:
        with pytest.raises(ValueError, match="pool cannot be empty"):
            tabular_strip([0.0], lambda x: 0.5, [])

    def test_rejects_invalid_nmix(self) -> None:
        with pytest.raises(ValueError, match="n_mix must be >= 1"):
            tabular_strip([0.0], lambda x: 0.5, [[0.0]], n_mix=0)

    def test_rejects_invalid_alpha_bounds(self) -> None:
        with pytest.raises(ValueError, match="alpha must be strictly in"):
            tabular_strip([0.0], lambda x: 0.5, [[0.0]], alpha=0.0)
        with pytest.raises(ValueError, match="alpha must be strictly in"):
            tabular_strip([0.0], lambda x: 0.5, [[0.0]], alpha=1.0)
        with pytest.raises(ValueError, match="alpha must be strictly in"):
            tabular_strip([0.0], lambda x: 0.5, [[0.0]], alpha=1.5)

    def test_rejects_pool_dimension_mismatch(self) -> None:
        with pytest.raises(ValueError, match="Dimension mismatch"):
            tabular_strip([0.0, 1.0], lambda x: 0.5, [[0.0, 1.0, 2.0]])

    def test_rejects_non_finite_vector(self) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            tabular_strip([0.0, float("nan")], lambda x: 0.5, [[0.0, 1.0]])


class TestM2StripDetectorClass:
    """Contract verification for M2StripDetector class."""

    def test_detector_detect_with_callable_model(self) -> None:
        cfg = M2Config(n_mix=8, alpha=0.2, sampling_seed=123)
        detector = M2StripDetector(cfg)

        def dummy_model(x: list[float]) -> float:
            return 0.8

        vec = [0.0] * 2381
        res = detector.detect(vec, model_service=dummy_model)

        assert isinstance(res, SignalResult)
        assert res.name == "m2"
        assert 0.0 <= res.score <= 1.0
        assert res.diagnostics["formula"] == "tabular_strip"
        assert res.diagnostics["n_mix"] == 8
        assert res.diagnostics["alpha"] == 0.2
        assert res.diagnostics["sampling_seed"] == 123

    def test_detector_detect_with_infer_method_model(self) -> None:
        class MockModelService:
            def infer(self, x: list[float]) -> tuple[float, list[float]]:
                return 0.9, [0.0] * len(x)

        detector = M2StripDetector(model_service=MockModelService())
        vec = [0.0] * 2381
        res = detector.detect(vec)
        assert res.score > 0.0
        assert res.diagnostics["average_entropy"] < 0.5

    def test_detector_missing_model_raises(self) -> None:
        detector = M2StripDetector()
        with pytest.raises(ValueError, match="requires a model_service"):
            detector.detect([0.0] * 2381)

    def test_detector_disabled_returns_zero(self) -> None:
        cfg = M2Config(enabled=False)
        detector = M2StripDetector(cfg)
        res = detector.detect([0.0] * 2381)
        assert res.score == 0.0
        assert res.diagnostics["status"] == "DISABLED"

    def test_detector_score_convenience_method(self) -> None:
        detector = M2StripDetector()
        score = detector.score([0.0] * 2381, model_service=lambda x: 1.0)
        assert score == 1.0

    def test_detector_with_real_demo_model_service_regression(self) -> None:
        from x_sentinel.model.demo import DemoModelService

        detector = M2StripDetector(model_service=DemoModelService())
        vec = [0.0] * 2381
        res = detector.detect(vec)
        assert isinstance(res.score, float)
        assert 0.0 <= res.score <= 1.0
        assert "average_entropy" in res.diagnostics

    def test_detector_with_real_lightgbm_service_regression(self) -> None:
        from pathlib import Path

        from x_sentinel.model.lightgbm_service import LightGBMService

        model_path = Path("datasets/ember2018/ember_model_2018.txt")
        if not model_path.exists():
            pytest.skip("Ember 2018 model artifact not found")

        lgb_service = LightGBMService(
            model_path=model_path,
            expected_sha256="509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2",
        )
        detector = M2StripDetector(model_service=lgb_service)
        vec = [0.0] * 2381
        res = detector.detect(vec)
        assert isinstance(res.score, float)
        assert 0.0 <= res.score <= 1.0
        assert "average_entropy" in res.diagnostics
