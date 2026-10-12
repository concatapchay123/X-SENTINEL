from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from x_sentinel.data.views import load_view_map
from x_sentinel.detection.pipeline import DetectorPipeline
from x_sentinel.domain import AnalysisResult
from x_sentinel.fusion import (
    CalibrationEngine,
    DecisionPolicy,
    DecisionVerdict,
    FusionEngine,
    load_fusion_config,
)
from x_sentinel.model.demo import DemoModelService


class TestDetectorToFusionIntegration:
    """Full end-to-end integration across DetectorPipeline, FusionEngine, and DecisionPolicy."""

    def test_pipeline_to_fusion_and_decision_lifecycle(self) -> None:
        view_map = load_view_map(Path("configs/views.demo.yaml"), allow_demo=True)
        model_service = DemoModelService()
        pipeline = DetectorPipeline(view_map=view_map, model_service=model_service)

        fusion_cfg = load_fusion_config("configs/detector.yaml")
        fusion_engine = FusionEngine(fusion_cfg.fusion)
        calib_engine = CalibrationEngine(fusion_cfg.calibration, demo_mode=True)
        threshold = calib_engine.resolve()

        decision_policy = DecisionPolicy(
            alert_threshold=threshold,
            quarantine_threshold=calib_engine.quarantine_threshold,
            demo_mode=True,
        )

        vector = [0.0] * 2381
        vector[0] = 100.0  # SizeOfRawData
        vector[1] = 50.0  # VirtualAddress

        # Step 1: Detector pipeline evaluation
        signals = pipeline.scores(vector, model_service=model_service, view_map=view_map)
        assert len(signals) == 5
        assert set(signals.keys()) == {"m1", "m2", "m3", "m4", "m5"}
        for s in signals.values():
            assert 0.0 <= s <= 1.0

        # Step 2: Signal Fusion
        fusion_result = fusion_engine.evaluate(signals)
        assert 0.0 <= fusion_result.score <= 1.0
        assert fusion_result.strategy == "weighted_sum"

        # Step 3: Decision Policy
        decision_result = decision_policy.evaluate(fusion_result.score)
        assert decision_result.demo_mode is True
        assert decision_result.decision == DecisionVerdict.DEMO_ONLY.value
        assert decision_result.candidate_verdict in ("PASS", "ALERT", "QUARANTINE")

        # Step 4: Construct canonical AnalysisResult
        analysis = AnalysisResult(
            request_id=str(uuid.uuid4()),
            status=decision_result.decision,
            demo_mode=True,
            malware_score=0.10,
            signals=signals,
            suspicion_score=fusion_result.score,
            threshold=threshold,
            view_contributions={"structural": 0.1, "behavioral": 0.2, "metadata": 0.7},
            warnings=decision_result.warnings,
        )
        assert analysis.status == "DEMO_ONLY"
        assert analysis.suspicion_score == fusion_result.score

    def test_pipeline_zero_jev_ai_dependency(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that the fusion and decision layers make zero external HTTP/AI calls."""
        import httpx

        def forbidden_call(*args, **kwargs):
            raise AssertionError("External HTTP / AI call forbidden during detector fusion!")

        monkeypatch.setattr(httpx, "post", forbidden_call)
        monkeypatch.setattr(httpx, "get", forbidden_call)
        monkeypatch.setattr(httpx.Client, "post", forbidden_call)
        monkeypatch.setattr(httpx.Client, "get", forbidden_call)

        fusion_engine = FusionEngine()
        signals = {"m1": 0.2, "m2": 0.3, "m3": 0.1, "m4": 0.2, "m5": 0.1}
        score = fusion_engine.score(signals)
        policy = DecisionPolicy(alert_threshold=0.50, quarantine_threshold=0.85, demo_mode=False)
        decision = policy.evaluate(score)

        assert decision.decision == "PASS"

    def test_db_schema_decision_allowed_constraint_compatibility(self) -> None:
        """Verify that verdicts produced conform to database check constraint."""
        allowed_db_decisions = {"unknown", "pass", "alert", "quarantine"}
        policy = DecisionPolicy(alert_threshold=0.50, quarantine_threshold=0.85, demo_mode=False)

        scores_to_test = [0.10, 0.50, 0.90]
        for s in scores_to_test:
            res = policy.evaluate(s)
            # Map canonical uppercase to lowercase for DB storage
            db_verdict = res.decision.lower()
            assert db_verdict in allowed_db_decisions
