from __future__ import annotations

import math
from typing import Any, Sequence

from x_sentinel.detection.config import M4Config
from x_sentinel.domain import SignalResult


def symmetric_cross_view_disagreement(
    view_scores: dict[str, float] | Sequence[float],
) -> float:
    """Canonical M4 Strategy: Symmetric Cross-View Disagreement across 3 views (ADR-005).

    Mathematical formulation:
        For 3 view signals y1, y2, y3 in [0, 1]:
        disagreement = 0.5 * (|y1 - y2| + |y2 - y3| + |y3 - y1|)

    Properties:
        - Symmetric under all permutations of view indices.
        - Exactly 0.0 when all three views agree (y1 == y2 == y3).
        - Exactly 1.0 when one view maximally diverges from the others (e.g. [1, 0, 0]).
        - Bounded in [0.0, 1.0].
    """
    vals = _extract_3_views(view_scores)
    y1, y2, y3 = vals[0], vals[1], vals[2]
    diff12 = abs(y1 - y2)
    diff23 = abs(y2 - y3)
    diff31 = abs(y3 - y1)
    disagreement = 0.5 * (diff12 + diff23 + diff31)
    return float(min(max(disagreement, 0.0), 1.0))


def view_std(view_scores: dict[str, float] | Sequence[float]) -> float:
    """Ablation strategy (T2): Standard deviation of the 3 view signals."""
    vals = _extract_3_views(view_scores)
    mean_val = sum(vals) / 3.0
    var = sum((v - mean_val) ** 2 for v in vals) / 3.0
    return float(math.sqrt(var))


def max_pairwise_difference(view_scores: dict[str, float] | Sequence[float]) -> float:
    """Ablation strategy: Maximum pairwise absolute difference among views."""
    vals = _extract_3_views(view_scores)
    diffs = [abs(vals[0] - vals[1]), abs(vals[1] - vals[2]), abs(vals[2] - vals[0])]
    return float(max(diffs))


def behavioral_metadata_gap(
    view_scores: dict[str, float] | Sequence[float],
) -> float:
    """Ablation strategy (T1): Behavioral vs. Metadata discrepancy / classifier gap.

    Formula:
        gap = |y_behavioral - y_metadata|
    """
    if isinstance(view_scores, dict):
        if "behavioral" in view_scores and "metadata" in view_scores:
            b = float(view_scores["behavioral"])
            m = float(view_scores["metadata"])
            return float(abs(b - m))
    vals = _extract_3_views(view_scores)
    # By standard order [structural, behavioral, metadata]: index 1 and 2
    return float(abs(vals[1] - vals[2]))


def full_vs_behavioral_gap(
    full_score: float,
    behavioral_score: float,
) -> float:
    """Ablation strategy (T3): Full model vs. Behavioral view gap.

    Formula:
        gap = |y_full - y_behavioral|
    """
    f = float(full_score)
    b = float(behavioral_score)
    if not (math.isfinite(f) and math.isfinite(b)):
        raise ValueError("Scores must be finite.")
    return float(abs(f - b))


def _extract_3_views(view_scores: dict[str, float] | Sequence[float]) -> list[float]:
    if isinstance(view_scores, dict):
        # Look for standard keys first
        if "structural" in view_scores and "behavioral" in view_scores and "metadata" in view_scores:
            vals = [
                float(view_scores["structural"]),
                float(view_scores["behavioral"]),
                float(view_scores["metadata"]),
            ]
        else:
            if len(view_scores) != 3:
                raise ValueError(f"Expected 3 view signals, got {len(view_scores)}")
            vals = [float(v) for v in view_scores.values()]
    elif isinstance(view_scores, (list, tuple)):
        if len(view_scores) != 3:
            raise ValueError(f"Expected 3 view signals, got {len(view_scores)}")
        vals = [float(v) for v in view_scores]
    else:
        raise TypeError(f"Invalid view_scores type: {type(view_scores)}")

    for idx, v in enumerate(vals):
        if not math.isfinite(v):
            raise ValueError(f"View signal at index {idx} is non-finite: {v}")
    return vals


class M4CrossViewDetector:
    """Canonical M4 Detector: Cross-View Semantic Consistency and Disagreement.

    Implements ADR-005 frozen canonical strategy: 'symmetric_disagreement',
    while supporting historical variants as ablation plugins.
    """

    name: str = "m4"

    def __init__(self, config: M4Config | dict[str, Any] | None = None) -> None:
        if config is None:
            self.config = M4Config()
        elif isinstance(config, M4Config):
            self.config = config
        elif isinstance(config, dict):
            strategy = config.get("strategy", "symmetric_disagreement")
            self.config = M4Config(
                enabled=bool(config.get("enabled", True)),
                strategy=str(strategy),
                ablation_strategies=list(
                    config.get(
                        "ablation_strategies",
                        [
                            "view_std",
                            "behavioral_metadata_gap",
                            "full_vs_behavioral_gap",
                            "max_pairwise_difference",
                        ],
                    )
                ),
            )
        else:
            raise TypeError(f"Invalid config type: {type(config)}")

    def score(
        self,
        view_scores: dict[str, float] | Sequence[float],
        full_score: float | None = None,
    ) -> float:
        res = self.detect(view_scores, full_score=full_score)
        return res.score

    def detect(
        self,
        view_scores: dict[str, float] | Sequence[float],
        full_score: float | None = None,
    ) -> SignalResult:
        if not self.config.enabled:
            return SignalResult(name=self.name, score=0.0, diagnostics={"status": "DISABLED"})

        strat = self.config.strategy
        vals = _extract_3_views(view_scores)

        if strat == "symmetric_disagreement":
            score = symmetric_cross_view_disagreement(vals)
        elif strat == "view_std":
            score = view_std(vals)
        elif strat == "behavioral_metadata_gap":
            score = behavioral_metadata_gap(view_scores)
        elif strat == "full_vs_behavioral_gap":
            if full_score is None:
                raise ValueError("full_score is required for full_vs_behavioral_gap strategy")
            score = full_vs_behavioral_gap(full_score, vals[1])
        elif strat == "max_pairwise_difference":
            score = max_pairwise_difference(vals)
        else:
            raise ValueError(f"Unrecognized strategy: {strat}")

        diff12 = abs(vals[0] - vals[1])
        diff23 = abs(vals[1] - vals[2])
        diff31 = abs(vals[2] - vals[0])

        diagnostics: dict[str, Any] = {
            "formula": "cross_view_disagreement",
            "strategy": strat,
            "is_canonical": (strat == "symmetric_disagreement"),
            "view_values": {
                "structural": vals[0],
                "behavioral": vals[1],
                "metadata": vals[2],
            },
            "pairwise_differences": {
                "structural_vs_behavioral": diff12,
                "behavioral_vs_metadata": diff23,
                "metadata_vs_structural": diff31,
            },
            "view_std": float(view_std(vals)),
            "max_difference": float(max([diff12, diff23, diff31])),
        }

        return SignalResult(name=self.name, score=score, diagnostics=diagnostics)
