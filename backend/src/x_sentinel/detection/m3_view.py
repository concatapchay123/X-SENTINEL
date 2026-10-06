from __future__ import annotations


def view_contributions(shap_by_view: dict[str, list[float]]) -> dict[str, float]:
    totals = {k: sum(abs(float(v)) for v in vals) for k, vals in shap_by_view.items()}
    denom = sum(totals.values())
    if denom <= 1e-12:
        return {k: 0.0 for k in totals}
    return {k: v / denom for k, v in totals.items()}


def m3_view_concentration(contrib: dict[str, float]) -> float:
    """[PROPOSED demo/interface form] max semantic-view contribution."""
    return max(contrib.values(), default=0.0)
