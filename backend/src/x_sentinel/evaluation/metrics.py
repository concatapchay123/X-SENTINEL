from __future__ import annotations


def attack_success_rate(successes: int, total: int) -> float:
    if total <= 0:
        raise ValueError("total must be positive")
    return successes / total


def false_positive_rate(false_positives: int, benign_total: int) -> float:
    if benign_total <= 0:
        raise ValueError("benign_total must be positive")
    return false_positives / benign_total
