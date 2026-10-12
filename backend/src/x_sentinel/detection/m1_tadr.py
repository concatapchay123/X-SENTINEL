from __future__ import annotations

import math
from typing import Any, Sequence

from x_sentinel.detection.config import M1Config
from x_sentinel.domain import SignalResult


def m1_tadr(shap_values: Sequence[float], eps: float = 1e-12) -> float:
    """Top-1 Attribution Dominance Ratio (Severi et al. / X-GUARD baseline).

    Mathematical formulation:
        TADR(S) = max_i(|s_i|) / sum_i(|s_i|)

    When sum_i(|s_i|) <= eps, returns 0.0 to prevent division by zero.
    Bounded in [0.0, 1.0].
    """
    if not isinstance(shap_values, (list, tuple)):
        # Support numpy arrays or general sequences
        try:
            shap_values = list(shap_values)
        except Exception as err:
            raise TypeError(f"shap_values must be a sequence of floats, got {type(shap_values)}") from err

    if len(shap_values) == 0:
        raise ValueError("shap_values cannot be empty.")

    abs_values: list[float] = []
    for idx, v in enumerate(shap_values):
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise TypeError(f"Feature at index {idx} has invalid non-numeric type: {type(v)}")
        val = float(v)
        if not math.isfinite(val):
            raise ValueError(f"Feature at index {idx} has non-finite value: {val}")
        abs_values.append(abs(val))

    total = sum(abs_values)
    if total <= eps:
        return 0.0

    score = max(abs_values) / total
    return float(min(max(score, 0.0), 1.0))


class M1TADRDetector:
    """Canonical M1 Detector: Top-1 Attribution Dominance Ratio."""

    name: str = "m1"

    def __init__(self, config: M1Config | dict[str, Any] | None = None) -> None:
        if config is None:
            self.config = M1Config()
        elif isinstance(config, M1Config):
            self.config = config
        elif isinstance(config, dict):
            self.config = M1Config(
                enabled=bool(config.get("enabled", True)),
                formula=str(config.get("formula", "tadr")),
                eps=float(config.get("eps", 1e-12)),
            )
        else:
            raise TypeError(f"Invalid config type: {type(config)}")

    def score(self, shap_values: Sequence[float]) -> float:
        return m1_tadr(shap_values, eps=self.config.eps)

    def detect(self, shap_values: Sequence[float]) -> SignalResult:
        if not self.config.enabled:
            return SignalResult(name=self.name, score=0.0, diagnostics={"status": "DISABLED"})

        if not isinstance(shap_values, (list, tuple)):
            shap_values = list(shap_values)

        abs_vals = [abs(float(v)) for v in shap_values]
        total = sum(abs_vals)
        top_val = max(abs_vals) if abs_vals else 0.0
        top_idx = abs_vals.index(top_val) if abs_vals else -1

        tadr_score = m1_tadr(shap_values, eps=self.config.eps)

        diagnostics: dict[str, Any] = {
            "formula": "tadr",
            "top_feature_index": top_idx,
            "top_feature_abs_shap": float(top_val),
            "total_abs_shap": float(total),
            "feature_count": len(shap_values),
            "eps": self.config.eps,
        }

        return SignalResult(name=self.name, score=tadr_score, diagnostics=diagnostics)
