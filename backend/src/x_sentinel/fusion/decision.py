from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class DecisionVerdict(StrEnum):
    """Canonical decision verdicts in X-SENTINEL V3."""

    PASS = "PASS"
    ALERT = "ALERT"
    QUARANTINE = "QUARANTINE"
    DEMO_ONLY = "DEMO_ONLY"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ThresholdProvenance:
    """Provenance tracking for calibrated or configured decision thresholds."""

    threshold_id: str
    value: float
    mode: str
    source: str
    version: str
    config_hash: str
    fpr_target: float | None = None
    empirical_fpr: float | None = None
    wilson_ci: tuple[float, float] | None = None
    artifact_hash: str | None = None


@dataclass(frozen=True)
class DecisionResult:
    """Canonical decision outcome with audit trail and threshold provenance."""

    decision: str
    suspicion_score: float
    threshold_applied: float | None
    quarantine_threshold_applied: float | None
    demo_mode: bool
    candidate_verdict: str
    provenance: ThresholdProvenance | None = None
    warnings: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)


def decision_from_score(score: float, threshold: float | None, demo_mode: bool) -> str:
    """Canonical decision function maintaining full backward compatibility.

    Args:
        score: Calibrated suspicion score in [0.0, 1.0].
        threshold: Alert threshold in [0.0, 1.0] or None.
        demo_mode: Boolean indicating if system is running in demo mode.

    Returns:
        str: 'DEMO_ONLY', 'ALERT', or 'PASS'.
    """
    if demo_mode:
        return DecisionVerdict.DEMO_ONLY.value
    if threshold is None:
        raise RuntimeError("scientific threshold unresolved")
    return DecisionVerdict.ALERT.value if score >= threshold else DecisionVerdict.PASS.value


class DecisionPolicy:
    """Canonical decision engine applying frozen thresholds, 3-state logic, and provenance."""

    def __init__(
        self,
        alert_threshold: float | None,
        quarantine_threshold: float = 0.85,
        provenance: ThresholdProvenance | None = None,
        demo_mode: bool = False,
    ) -> None:
        self.alert_threshold = alert_threshold
        self.quarantine_threshold = float(quarantine_threshold)
        self.provenance = provenance
        self.demo_mode = demo_mode

        if self.alert_threshold is not None:
            if not (0.0 <= self.alert_threshold <= 1.0):
                raise ValueError(
                    f"alert_threshold must be in [0.0, 1.0], got {self.alert_threshold}."
                )
        if not (0.0 <= self.quarantine_threshold <= 1.0):
            raise ValueError(
                f"quarantine_threshold must be in [0.0, 1.0], got {self.quarantine_threshold}."
            )
        if self.alert_threshold is not None and self.quarantine_threshold < self.alert_threshold:
            raise ValueError(
                f"quarantine_threshold ({self.quarantine_threshold}) cannot be less than "
                f"alert_threshold ({self.alert_threshold})."
            )

    def evaluate(
        self,
        suspicion_score: float,
        malware_score: float | None = None,
    ) -> DecisionResult:
        """Evaluate suspicion score against decision policy boundaries.

        Boundaries:
            - suspicion_score < alert_threshold: PASS
            - alert_threshold <= suspicion_score < quarantine_threshold: ALERT
            - suspicion_score >= quarantine_threshold: QUARANTINE
        """
        try:
            f_score = float(suspicion_score)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"suspicion_score must be numeric, got {suspicion_score}.") from exc

        if not math.isfinite(f_score):
            raise ValueError(f"suspicion_score must be finite, got {f_score}.")
        if not (0.0 <= f_score <= 1.0):
            raise ValueError(f"suspicion_score must be in [0.0, 1.0], got {f_score}.")

        # Determine mathematical candidate verdict
        thresh = self.alert_threshold if self.alert_threshold is not None else 0.50
        q_thresh = self.quarantine_threshold

        if f_score >= q_thresh:
            candidate = DecisionVerdict.QUARANTINE.value
        elif f_score >= thresh:
            candidate = DecisionVerdict.ALERT.value
        else:
            candidate = DecisionVerdict.PASS.value

        if self.demo_mode:
            return DecisionResult(
                decision=DecisionVerdict.DEMO_ONLY.value,
                suspicion_score=f_score,
                threshold_applied=thresh,
                quarantine_threshold_applied=q_thresh,
                demo_mode=True,
                candidate_verdict=candidate,
                provenance=self.provenance,
                warnings=["DEMO_MODE_NOT_SCIENTIFIC_EVIDENCE"],
                diagnostics={"candidate_verdict": candidate, "malware_score": malware_score},
            )

        if self.alert_threshold is None:
            raise RuntimeError("scientific threshold unresolved")

        return DecisionResult(
            decision=candidate,
            suspicion_score=f_score,
            threshold_applied=thresh,
            quarantine_threshold_applied=q_thresh,
            demo_mode=False,
            candidate_verdict=candidate,
            provenance=self.provenance,
            warnings=[],
            diagnostics={"candidate_verdict": candidate, "malware_score": malware_score},
        )
