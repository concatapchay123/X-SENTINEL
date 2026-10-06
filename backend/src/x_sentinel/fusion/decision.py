from __future__ import annotations


def decision_from_score(score: float, threshold: float | None, demo_mode: bool) -> str:
    if demo_mode:
        return "DEMO_ONLY"
    if threshold is None:
        raise RuntimeError("scientific threshold unresolved")
    return "ALERT" if score >= threshold else "PASS"
