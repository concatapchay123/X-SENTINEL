from __future__ import annotations

import math
from typing import Any, Sequence

from x_sentinel.detection.config import M3Config
from x_sentinel.domain import SignalResult


def view_contributions(
    shap_by_view: dict[str, Sequence[float]], eps: float = 1e-12
) -> dict[str, float]:
    """Calculate normalized absolute SHAP attribution contribution per semantic view.

    Formula:
        total(v) = sum_{j in v} |s_j|
        C(v) = total(v) / (sum_{u} total(u))

    When total attribution <= eps, returns 0.0 for all views.
    Normalized so sum(C(v)) == 1.0 when total > eps.
    """
    if not isinstance(shap_by_view, dict):
        raise TypeError(f"shap_by_view must be a dict, got {type(shap_by_view)}")

    totals: dict[str, float] = {}
    for view_name, vals in shap_by_view.items():
        if not isinstance(vals, (list, tuple)):
            try:
                vals = list(vals)
            except Exception as err:
                raise TypeError(f"View '{view_name}' values must be a sequence") from err

        abs_sum = 0.0
        for idx, v in enumerate(vals):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise TypeError(f"View '{view_name}' at index {idx} has non-numeric value: {type(v)}")
            f_val = float(v)
            if not math.isfinite(f_val):
                raise ValueError(f"View '{view_name}' at index {idx} has non-finite value: {f_val}")
            abs_sum += abs(f_val)
        totals[str(view_name)] = abs_sum

    denom = sum(totals.values())
    if denom <= eps:
        return {k: 0.0 for k in totals}
    return {k: float(v / denom) for k, v in totals.items()}


def m3_view_concentration(contrib: dict[str, float]) -> float:
    """Maximum semantic-view attribution concentration.

    Formula:
        Concentration = max_{v} C(v)
    Bounded in [0.0, 1.0].
    """
    if not isinstance(contrib, dict):
        raise TypeError(f"contrib must be a dict, got {type(contrib)}")
    if not contrib:
        return 0.0
    return float(max(contrib.values(), default=0.0))


def view_entropy(contrib: dict[str, float], eps: float = 1e-12) -> float:
    """Compute Shannon entropy across semantic view contributions in bits.

    Formula:
        H(C) = - sum_{v: C(v) > eps} C(v) * log2(C(v))
    """
    if not isinstance(contrib, dict):
        raise TypeError(f"contrib must be a dict, got {type(contrib)}")
    h = 0.0
    for v in contrib.values():
        if v > eps:
            h -= float(v) * math.log2(float(v))
    return float(max(h, 0.0))


class M3ViewDetector:
    """Canonical M3 Detector: Semantic View Contribution and Concentration."""

    name: str = "m3"

    def __init__(self, config: M3Config | dict[str, Any] | None = None) -> None:
        if config is None:
            self.config = M3Config()
        elif isinstance(config, M3Config):
            self.config = config
        elif isinstance(config, dict):
            self.config = M3Config(
                enabled=bool(config.get("enabled", True)),
                aggregation=str(config.get("aggregation", "absolute_shap_sum_by_view")),
                metric=str(config.get("metric", "max_concentration")),
                eps=float(config.get("eps", 1e-12)),
            )
        else:
            raise TypeError(f"Invalid config type: {type(config)}")

    def _prepare_views(
        self,
        shap_input: dict[str, Sequence[float]] | Sequence[float],
        view_map: Any = None,
    ) -> dict[str, Sequence[float]]:
        if isinstance(shap_input, dict):
            return shap_input
        if view_map is not None and hasattr(view_map, "split"):
            return view_map.split(shap_input)
        if view_map is not None and hasattr(view_map, "structural"):
            shap_list = list(shap_input)

            def _extract_view(spec: Any) -> list[float]:
                if hasattr(spec, "extract"):
                    return list(spec.extract(shap_list))
                return shap_list[spec.start : spec.stop]

            return {
                "structural": _extract_view(view_map.structural),
                "behavioral": _extract_view(view_map.behavioral),
                "metadata": _extract_view(view_map.metadata),
            }
        raise ValueError(
            "M3 requires either a dict of {view_name: shap_values} or a flat SHAP vector with view_map."
        )

    def score(
        self,
        shap_input: dict[str, Sequence[float]] | Sequence[float],
        view_map: Any = None,
    ) -> float:
        res = self.detect(shap_input, view_map=view_map)
        return res.score

    def detect(
        self,
        shap_input: dict[str, Sequence[float]] | Sequence[float],
        view_map: Any = None,
    ) -> SignalResult:
        if not self.config.enabled:
            return SignalResult(name=self.name, score=0.0, diagnostics={"status": "DISABLED"})

        views = self._prepare_views(shap_input, view_map=view_map)
        contrib = view_contributions(views, eps=self.config.eps)
        concentration = m3_view_concentration(contrib)
        v_entropy = view_entropy(contrib, eps=self.config.eps)

        dominant_view = max(contrib.items(), key=lambda kv: kv[1])[0] if contrib else "none"

        diagnostics: dict[str, Any] = {
            "formula": "view_concentration",
            "aggregation": self.config.aggregation,
            "metric": self.config.metric,
            "contributions": contrib,
            "dominant_view": dominant_view,
            "view_entropy": v_entropy,
            "eps": self.config.eps,
        }

        return SignalResult(name=self.name, score=concentration, diagnostics=diagnostics)
