from __future__ import annotations

from pathlib import Path

import pytest
from x_sentinel.data.views import load_view_map
from x_sentinel.detection.config import (
    DetectorConfig,
    compute_detector_config_hash,
    load_detector_config,
)
from x_sentinel.detection.pipeline import DetectorPipeline
from x_sentinel.domain import SignalResult


class TestDetectorConfigLoading:
    """Verification of typed detector configuration parsing and validation."""

    def test_load_canonical_detector_yaml(self) -> None:
        cfg = load_detector_config("configs/detector.yaml")
        assert isinstance(cfg, DetectorConfig)
        assert cfg.status in ("PARTIAL_BASELINE", "FROZEN_DETECTOR_CORE")
        assert cfg.m1.enabled is True
        assert cfg.m1.formula == "tadr"
        assert cfg.m2.enabled is True
        assert cfg.m2.formula == "tabular_strip"
        assert cfg.m2.n_mix == 16
        assert cfg.m2.alpha == 0.2
        assert cfg.m3.enabled is True
        assert cfg.m3.aggregation == "absolute_shap_sum_by_view"
        assert cfg.m4.enabled is True
        assert cfg.m4.strategy == "symmetric_disagreement"
        assert cfg.m5.enabled is True
        assert cfg.m5.rules_sha256 == "2e8c599aa9fded31c8d27eb0d96f45743a087572f696bc8e3bdb0f69d5ca184d"

    def test_detector_config_hash_deterministic(self) -> None:
        h1 = compute_detector_config_hash("configs/detector.yaml")
        h2 = compute_detector_config_hash("configs/detector.yaml")
        assert h1 == h2
        assert len(h1) == 64

    def test_rejects_missing_config_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_detector_config("configs/non_existent.yaml")

    def test_rejects_invalid_m1_formula(self) -> None:
        with pytest.raises(ValueError, match="Unsupported M1 formula"):
            load_detector_config({"m1": {"formula": "unapproved_formula"}})

    def test_rejects_invalid_m2_alpha(self) -> None:
        with pytest.raises(ValueError, match="strictly in"):
            load_detector_config({"m2": {"alpha": 1.5}})

    def test_rejects_invalid_m4_strategy(self) -> None:
        with pytest.raises(ValueError, match="Unsupported M4 strategy"):
            load_detector_config({"m4": {"strategy": "random_guess"}})

    def test_load_config_with_explicit_null_and_string_booleans(self) -> None:
        cfg = load_detector_config({
            "m1": {"enabled": None},
            "m2": {"enabled": "true", "invert_entropy": "0"},
            "m3": {"enabled": False},
            "m4": {"enabled": "false"},
            "m5": {"enabled": "yes", "rules_file": "configs/m5_rules.json", "rules_sha256": "2e8c599aa9fded31c8d27eb0d96f45743a087572f696bc8e3bdb0f69d5ca184d"},
        })
        assert cfg.m1.enabled is True
        assert cfg.m2.enabled is True
        assert cfg.m2.invert_entropy is False
        assert cfg.m3.enabled is False
        assert cfg.m4.enabled is False
        assert cfg.m5.enabled is True


class TestDetectorPipelineIntegration:
    """Verification of the unified DetectorPipeline coordinating M1-M5."""

    @pytest.fixture
    def mock_model(self):
        class MockModel:
            def infer(self, x: list[float]) -> tuple[float, list[float]]:
                # Return fixed malware score and synthetic SHAP vector
                shap = [0.001 * (i % 5) for i in range(len(x))]
                shap[10] = 0.5  # Feature in structural view
                return 0.75, shap

        return MockModel()

    def test_pipeline_evaluate_all_signals(self, mock_model) -> None:
        view_map = load_view_map(Path("configs/views.demo.yaml"), allow_demo=True)
        pipeline = DetectorPipeline(
            config="configs/detector.yaml",
            model_service=mock_model,
            view_map=view_map,
        )

        vector = [0.0] * 2381
        results = pipeline.evaluate(vector)

        # All 5 signals must be present
        for sig in ["m1", "m2", "m3", "m4", "m5"]:
            assert sig in results
            assert isinstance(results[sig], SignalResult)
            assert results[sig].name == sig
            assert 0.0 <= results[sig].score <= 1.0

        # Detailed signal verification
        assert results["m1"].score > 0.0
        assert results["m2"].score >= 0.0
        assert results["m3"].score > 0.0
        assert results["m4"].score >= 0.0
        assert results["m5"].score == 1.0  # Clean zero vector satisfies all rules

    def test_pipeline_scores_convenience_method(self, mock_model) -> None:
        view_map = load_view_map(Path("configs/views.demo.yaml"), allow_demo=True)
        pipeline = DetectorPipeline(
            config="configs/detector.yaml",
            model_service=mock_model,
            view_map=view_map,
        )

        scores = pipeline.scores([0.0] * 2381)
        assert set(scores.keys()) == {"m1", "m2", "m3", "m4", "m5"}
        for val in scores.values():
            assert isinstance(val, float)
            assert 0.0 <= val <= 1.0

    def test_pipeline_zero_jev_ai_dependency(self, mock_model, monkeypatch) -> None:
        # Guarantee pipeline runs with zero network / AI calls
        import socket

        def guarded_connect(*_args, **_kwargs):
            raise RuntimeError("NETWORK CALL FORBIDDEN IN DETECTOR CORE")

        monkeypatch.setattr(socket.socket, "connect", guarded_connect)

        view_map = load_view_map(Path("configs/views.demo.yaml"), allow_demo=True)
        pipeline = DetectorPipeline(
            config="configs/detector.yaml",
            model_service=mock_model,
            view_map=view_map,
        )
        scores = pipeline.scores([0.0] * 2381)
        assert len(scores) == 5

    def test_pipeline_determinism(self, mock_model) -> None:
        view_map = load_view_map(Path("configs/views.demo.yaml"), allow_demo=True)
        pipeline = DetectorPipeline(
            config="configs/detector.yaml",
            model_service=mock_model,
            view_map=view_map,
        )
        res1 = pipeline.scores([0.0] * 2381)
        res2 = pipeline.scores([0.0] * 2381)
        assert res1 == res2

    def test_pipeline_with_indices_spec_view_map_regression(self, mock_model) -> None:
        from x_sentinel.data.views import IndicesSpec, ViewMap

        indices_view_map = ViewMap(
            status="TEST",
            structural=IndicesSpec(indices=list(range(0, 1000))),
            behavioral=IndicesSpec(indices=list(range(1000, 2000))),
            metadata=IndicesSpec(indices=list(range(2000, 2381))),
        )
        pipeline = DetectorPipeline(
            config="configs/detector.yaml",
            model_service=mock_model,
            view_map=indices_view_map,
        )
        scores = pipeline.scores([0.0] * 2381)
        assert len(scores) == 5
        assert all(isinstance(v, float) and 0.0 <= v <= 1.0 for v in scores.values())

    def test_pipeline_with_real_demo_model_service_regression(self) -> None:
        from x_sentinel.model.demo import DemoModelService

        view_map = load_view_map(Path("configs/views.demo.yaml"), allow_demo=True)
        pipeline = DetectorPipeline(
            config="configs/detector.yaml",
            model_service=DemoModelService(),
            view_map=view_map,
        )
        scores = pipeline.scores([0.0] * 2381)
        assert len(scores) == 5
        assert all(isinstance(v, float) and 0.0 <= v <= 1.0 for v in scores.values())

    def test_pipeline_with_real_lightgbm_service_regression(self) -> None:
        from x_sentinel.model.lightgbm_service import LightGBMService

        model_path = Path("datasets/ember2018/ember_model_2018.txt")
        if not model_path.exists():
            pytest.skip("Ember 2018 model artifact not found")

        lgb_service = LightGBMService(
            model_path=model_path,
            expected_sha256="509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2",
        )
        view_map = load_view_map(Path("configs/views.demo.yaml"), allow_demo=True)
        pipeline = DetectorPipeline(
            config="configs/detector.yaml",
            model_service=lgb_service,
            view_map=view_map,
        )
        scores = pipeline.scores([0.0] * 2381)
        assert len(scores) == 5
        assert all(isinstance(v, float) and 0.0 <= v <= 1.0 for v in scores.values())
