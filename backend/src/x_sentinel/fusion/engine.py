from __future__ import annotations


def demo_fusion(signals: dict[str, float]) -> float:
    """DEMO ONLY. Equal mean of available finite signals; never scientific evidence."""
    values = [float(v) for v in signals.values()]
    if not values:
        return 0.0
    return sum(values) / len(values)


class ScientificFusion:
    def score(self, *_args, **_kwargs) -> float:
        raise NotImplementedError("PLAN-15: scientific fusion/calibration must be frozen")
