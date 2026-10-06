from __future__ import annotations

import math


class DemoModelService:
    """Deterministic integration adapter. NOT scientific evidence."""

    def infer(self, vector: list[float]) -> tuple[float, list[float]]:
        # Stable bounded pseudo-score derived from simple vector statistics.
        mean = sum(vector) / max(len(vector), 1)
        score = 1.0 / (1.0 + math.exp(-max(min(mean, 20.0), -20.0)))
        shap = [float(v - mean) / max(len(vector), 1) for v in vector]
        return float(score), shap
