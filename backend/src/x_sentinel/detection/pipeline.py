from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from x_sentinel.data.schema import validate_vector
from x_sentinel.data.views import ViewMap, load_view_map
from x_sentinel.detection.config import DetectorConfig, load_detector_config
from x_sentinel.detection.m1_tadr import M1TADRDetector
from x_sentinel.detection.m2_strip import M2StripDetector
from x_sentinel.detection.m3_view import M3ViewDetector
from x_sentinel.detection.m4_cross_view import M4CrossViewDetector
from x_sentinel.detection.m5_semantic import M5SemanticPlausibilityDetector
from x_sentinel.domain import SignalResult


class DetectorPipeline:
    """Unified Detector Pipeline executing canonical M1-M5 signal extraction without AI dependencies."""

    def __init__(
        self,
        config: DetectorConfig | Path | str | dict[str, Any] | None = None,
        model_service: Any = None,
        view_map: ViewMap | None = None,
        benign_pool: Sequence[Sequence[float]] | None = None,
        view_map_path: Path | str | None = None,
    ) -> None:
        if isinstance(config, DetectorConfig):
            self.config = config
        else:
            self.config = load_detector_config(config)

        self.model_service = model_service

        self.view_map: ViewMap | None = None
        if view_map is not None:
            self.view_map = view_map
        elif view_map_path is not None:
            self.view_map = load_view_map(Path(view_map_path), allow_demo=True)
        else:
            demo_view_path = Path("configs/views.demo.yaml")
            if demo_view_path.exists():
                self.view_map = load_view_map(demo_view_path, allow_demo=True)
            else:
                self.view_map = None

        self.m1 = M1TADRDetector(self.config.m1)
        self.m2 = M2StripDetector(self.config.m2, benign_pool=benign_pool, model_service=model_service)
        self.m3 = M3ViewDetector(self.config.m3)
        self.m4 = M4CrossViewDetector(self.config.m4)
        self.m5 = M5SemanticPlausibilityDetector(self.config.m5)

    def evaluate(
        self,
        vector: Sequence[float],
        model_service: Any = None,
        shap_values: Sequence[float] | None = None,
        view_map: ViewMap | None = None,
        benign_pool: Sequence[Sequence[float]] | None = None,
    ) -> dict[str, SignalResult]:
        """Execute all enabled detector signals M1-M5 on input vector.

        Returns:
            dict mapping signal names ('m1', 'm2', 'm3', 'm4', 'm5') to SignalResult objects.
        """
        clean_vector = validate_vector(vector)
        target_model = model_service or self.model_service
        target_view_map = view_map or self.view_map

        # Obtain model prediction and local SHAP explanation if not provided
        model_score = 0.0
        shap: list[float] | None = None
        if shap_values is not None:
            shap = [float(v) for v in shap_values]
        elif target_model is not None and hasattr(target_model, "infer"):
            model_score, shap = target_model.infer(clean_vector)

        results: dict[str, SignalResult] = {}

        # M1: TADR (Attribution Dominance)
        if shap is not None:
            results["m1"] = self.m1.detect(shap)
        else:
            results["m1"] = SignalResult(
                name="m1", score=0.0, diagnostics={"status": "SKIPPED_NO_SHAP"}
            )

        # M2: Tabular STRIP (Inference-time perturbation)
        if target_model is not None:
            results["m2"] = self.m2.detect(
                clean_vector, model_service=target_model, benign_pool=benign_pool
            )
        else:
            results["m2"] = SignalResult(
                name="m2", score=0.0, diagnostics={"status": "SKIPPED_NO_MODEL"}
            )

        # M3: View Contribution & Concentration
        contrib: dict[str, float] = {}
        if shap is not None and target_view_map is not None:
            shap_views = target_view_map.split(shap)
            results["m3"] = self.m3.detect(shap_views)
            contrib = results["m3"].diagnostics.get("contributions", {})
        else:
            results["m3"] = SignalResult(
                name="m3", score=0.0, diagnostics={"status": "SKIPPED_NO_SHAP_OR_VIEWMAP"}
            )

        # M4: Cross-View Disagreement
        if contrib:
            results["m4"] = self.m4.detect(contrib, full_score=model_score)
        else:
            # Fallback to zeros for the three views
            fallback_views = {"structural": 0.0, "behavioral": 0.0, "metadata": 0.0}
            results["m4"] = self.m4.detect(fallback_views, full_score=model_score)

        # M5: Semantic Plausibility
        results["m5"] = self.m5.detect(clean_vector)

        return results

    def scores(
        self,
        vector: Sequence[float],
        model_service: Any = None,
        shap_values: Sequence[float] | None = None,
        view_map: ViewMap | None = None,
        benign_pool: Sequence[Sequence[float]] | None = None,
    ) -> dict[str, float]:
        """Convenience method returning a simple mapping of {signal_name: score_float}."""
        evaluated = self.evaluate(
            vector=vector,
            model_service=model_service,
            shap_values=shap_values,
            view_map=view_map,
            benign_pool=benign_pool,
        )
        return {k: v.score for k, v in evaluated.items()}
