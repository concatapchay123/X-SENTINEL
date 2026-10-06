from __future__ import annotations


def m1_tadr(shap_values: list[float], eps: float = 1e-12) -> float:
    """Top-1 Attribution Dominance Ratio: max(abs(S)) / sum(abs(S))."""
    abs_values = [abs(float(v)) for v in shap_values]
    total = sum(abs_values)
    if total <= eps:
        return 0.0
    return max(abs_values) / total
