from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from x_sentinel.evaluation.statistics import (
    WilsonCIResult,
    _delong_structural_components,
    validate_unique_sample_ids,
    wilson_ci,
)

CANONICAL_DECISIONS = frozenset({"PASS", "ALERT", "QUARANTINE"})
POSITIVE_DETECTOR_DECISIONS = frozenset({"ALERT", "QUARANTINE"})
ALLOWED_LATENCY_SCOPES = frozenset(
    {
        "detector_only",
        "end_to_end",
        "EndToEnd_WithSHAP",
        "EndToEnd_WithM5",
        "EndToEnd_WithJEV",
    }
)
ALLOWED_RECALL_KINDS = frozenset(
    {
        "conventional_malware",
        "triggered_malware",
        "successful_eligible_attack",
        "all_poisoned_test",
    }
)


class MetricError(ValueError):
    """Base error for scientific metric computation violations."""


class SingleClassPopulationError(MetricError):
    """Raised when AUROC is requested on a single-class label array."""


class ZeroDenominatorError(MetricError):
    """Raised when a rate metric has zero denominator samples."""


class ZeroEligibleSamplesError(ZeroDenominatorError):
    """Raised when zero malware samples pass the clean-model eligibility filter for ASR."""


class DemoDecisionRejectedError(MetricError):
    """Raised when a DEMO_ONLY decision is passed into scientific metric computation."""


class EvaluationLeakageError(MetricError):
    """Raised when calibration and evaluation sample sets overlap."""


def attack_success_rate(successes: int, total: int) -> float:
    """Computes simple attack success ratio with strict bounds validation."""
    if isinstance(successes, bool) or isinstance(total, bool):
        raise MetricError("successes and total must be integers, not booleans.")
    if total <= 0:
        raise ZeroDenominatorError("total must be > 0")
    if successes < 0 or successes > total:
        raise MetricError(f"successes must be in [0, {total}], got {successes}.")
    return float(successes) / float(total)


def false_positive_rate(false_positives: int, benign_total: int) -> float:
    """Computes simple false positive ratio with strict bounds validation."""
    if isinstance(false_positives, bool) or isinstance(benign_total, bool):
        raise MetricError("false_positives and benign_total must be integers, not booleans.")
    if benign_total <= 0:
        raise ZeroDenominatorError("benign_total must be > 0")
    if false_positives < 0 or false_positives > benign_total:
        raise MetricError(f"false_positives must be in [0, {benign_total}], got {false_positives}.")
    return float(false_positives) / float(benign_total)


def _validate_binary_labels(labels: Sequence[int], context: str) -> list[int]:
    if len(labels) == 0:
        raise MetricError(f"{context}: labels cannot be empty.")
    out: list[int] = []
    for idx, lbl in enumerate(labels):
        if isinstance(lbl, bool):
            raise MetricError(f"{context}: boolean label at index {idx} is forbidden; use 0 or 1.")
        if not isinstance(lbl, (int, np.integer)) or int(lbl) not in (0, 1):
            raise MetricError(
                f"{context}: invalid binary label at index {idx}: {lbl!r} (expected 0 or 1)."
            )
        out.append(int(lbl))
    return out


def _validate_finite_scores(scores: Sequence[float], context: str) -> list[float]:
    if len(scores) == 0:
        raise MetricError(f"{context}: scores cannot be empty.")
    out: list[float] = []
    for idx, val in enumerate(scores):
        if isinstance(val, bool) or not isinstance(val, (int, float, np.floating, np.integer)):
            raise MetricError(f"{context}: non-numeric score at index {idx}: {val!r}.")
        fval = float(val)
        if not math.isfinite(fval):
            raise MetricError(f"{context}: non-finite score (NaN/Inf) at index {idx}: {val!r}.")
        out.append(fval)
    return out


def _resolve_detector_flags(
    scores_or_decisions: Sequence[float | str],
    *,
    threshold: float | None,
    inclusive: bool,
    context: str,
) -> list[bool]:
    if len(scores_or_decisions) == 0:
        raise MetricError(f"{context}: scores_or_decisions cannot be empty.")
    if threshold is not None and (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float, np.floating, np.integer))
        or not math.isfinite(float(threshold))
    ):
        raise MetricError(
            f"{context}: threshold must be a finite numeric float, got {threshold!r}."
        )
    first = scores_or_decisions[0]
    if isinstance(first, str):
        flags: list[bool] = []
        for idx, item in enumerate(scores_or_decisions):
            if not isinstance(item, str):
                raise MetricError(
                    f"{context}: mixed types in scores_or_decisions at index {idx}: {item!r}."
                )
            dec = item.strip().upper()
            if dec == "DEMO_ONLY":
                raise DemoDecisionRejectedError(
                    f"{context}: 'DEMO_ONLY' decision at index {idx} "
                    "is forbidden in scientific evaluation."
                )
            if dec not in CANONICAL_DECISIONS:
                raise MetricError(
                    f"{context}: unknown decision '{item}' at index {idx}; "
                    f"expected {sorted(CANONICAL_DECISIONS)}."
                )
            flags.append(dec in POSITIVE_DETECTOR_DECISIONS)
        return flags

    if threshold is None:
        raise MetricError(
            f"{context}: a finite numeric threshold is required when evaluating raw scores."
        )
    thresh = float(threshold)
    numeric_scores = _validate_finite_scores(
        scores_or_decisions,  # type: ignore[arg-type]
        context=context,
    )
    if inclusive:
        return [s >= thresh for s in numeric_scores]
    return [s > thresh for s in numeric_scores]


def compute_auroc(
    labels: Sequence[int],
    scores: Sequence[float],
    *,
    higher_is_more_suspicious: bool = True,
    sample_ids: Sequence[str] | None = None,
) -> float:
    """Computes exact empirical AUROC without post-hoc score flipping."""
    clean_labels = _validate_binary_labels(labels, context="compute_auroc")
    if len(clean_labels) != len(scores):
        raise MetricError(
            f"compute_auroc: length mismatch between labels ({len(clean_labels)}) "
            f"and scores ({len(scores)})."
        )
    clean_scores = _validate_finite_scores(scores, context="compute_auroc")
    if sample_ids is not None:
        if len(sample_ids) != len(clean_labels):
            raise MetricError("compute_auroc: sample_ids length mismatch.")
        validate_unique_sample_ids(sample_ids, context="compute_auroc")

    y_arr = np.asarray(clean_labels, dtype=np.int64)
    s_arr = np.asarray(clean_scores, dtype=np.float64)
    if not higher_is_more_suspicious:
        s_arr = -s_arr

    pos_scores = s_arr[y_arr == 1]
    neg_scores = s_arr[y_arr == 0]
    if len(pos_scores) == 0 or len(neg_scores) == 0:
        raise SingleClassPopulationError(
            "AUROC requires both positive and negative classes "
            f"(got pos={len(pos_scores)}, neg={len(neg_scores)})."
        )

    auroc, _, _ = _delong_structural_components(pos_scores, neg_scores)
    return float(auroc)


@dataclass(frozen=True)
class FPRResult:
    """False Positive Rate result with exact counts and Wilson 95% CI (Task 14.11)."""

    fp: int
    tn: int
    benign_total: int
    fpr: float
    fpr_percent: float
    wilson_ci: WilsonCIResult
    threshold: float | None
    inclusive: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "fp": self.fp,
            "tn": self.tn,
            "benign_total": self.benign_total,
            "fpr": self.fpr,
            "fpr_percent": self.fpr_percent,
            "wilson_ci": self.wilson_ci.to_dict(),
            "threshold": self.threshold,
            "inclusive": self.inclusive,
        }


def compute_fpr(
    labels: Sequence[int],
    scores_or_decisions: Sequence[float | str],
    *,
    threshold: float | None = None,
    inclusive: bool = True,
    confidence: float = 0.95,
    sample_ids: Sequence[str] | None = None,
) -> FPRResult:
    """Computes False Positive Rate strictly over ground-truth benign (label=0) samples."""
    clean_labels = _validate_binary_labels(labels, context="compute_fpr")
    if len(clean_labels) != len(scores_or_decisions):
        raise MetricError(
            f"compute_fpr: length mismatch between labels ({len(clean_labels)}) "
            f"and scores_or_decisions ({len(scores_or_decisions)})."
        )
    if sample_ids is not None:
        if len(sample_ids) != len(clean_labels):
            raise MetricError("compute_fpr: sample_ids length mismatch.")
        validate_unique_sample_ids(sample_ids, context="compute_fpr")

    flags = _resolve_detector_flags(
        scores_or_decisions,
        threshold=threshold,
        inclusive=inclusive,
        context="compute_fpr",
    )

    fp = 0
    tn = 0
    for lbl, flagged in zip(clean_labels, flags, strict=True):
        if lbl == 0:
            if flagged:
                fp += 1
            else:
                tn += 1

    benign_total = fp + tn
    if benign_total == 0:
        raise ZeroDenominatorError("compute_fpr: zero benign (label=0) samples in population.")

    rate = false_positive_rate(fp, benign_total)
    ci = wilson_ci(fp, benign_total, confidence=confidence)
    return FPRResult(
        fp=fp,
        tn=tn,
        benign_total=benign_total,
        fpr=rate,
        fpr_percent=rate * 100.0,
        wilson_ci=ci,
        threshold=float(threshold) if threshold is not None else None,
        inclusive=inclusive,
    )


@dataclass(frozen=True)
class RecallResult:
    """Detector Recall result with explicit denominator semantics and Wilson CI (Task 14.11)."""

    tp: int
    fn: int
    positive_total: int
    recall: float
    recall_percent: float
    wilson_ci: WilsonCIResult
    recall_kind: str
    threshold: float | None
    inclusive: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "tp": self.tp,
            "fn": self.fn,
            "positive_total": self.positive_total,
            "recall": self.recall,
            "recall_percent": self.recall_percent,
            "wilson_ci": self.wilson_ci.to_dict(),
            "recall_kind": self.recall_kind,
            "threshold": self.threshold,
            "inclusive": self.inclusive,
        }


def compute_recall(
    labels: Sequence[int],
    scores_or_decisions: Sequence[float | str],
    *,
    threshold: float | None = None,
    inclusive: bool = True,
    eligible_mask: Sequence[bool] | None = None,
    recall_kind: str = "triggered_malware",
    confidence: float = 0.95,
    sample_ids: Sequence[str] | None = None,
) -> RecallResult:
    """Computes Detector Recall over positive samples (or eligible attack subset)."""
    if recall_kind not in ALLOWED_RECALL_KINDS:
        raise MetricError(
            f"Unsupported recall_kind '{recall_kind}'; "
            f"expected one of {sorted(ALLOWED_RECALL_KINDS)}."
        )
    if recall_kind == "successful_eligible_attack" and eligible_mask is None:
        raise MetricError(
            "compute_recall: eligible_mask is required when "
            "recall_kind='successful_eligible_attack' to prevent denominator substitution."
        )
    clean_labels = _validate_binary_labels(labels, context="compute_recall")
    if len(clean_labels) != len(scores_or_decisions):
        raise MetricError(
            f"compute_recall: length mismatch between labels ({len(clean_labels)}) "
            f"and scores_or_decisions ({len(scores_or_decisions)})."
        )
    if eligible_mask is not None and len(eligible_mask) != len(clean_labels):
        raise MetricError("compute_recall: eligible_mask length must match labels length.")
    if sample_ids is not None:
        if len(sample_ids) != len(clean_labels):
            raise MetricError("compute_recall: sample_ids length mismatch.")
        validate_unique_sample_ids(sample_ids, context="compute_recall")

    flags = _resolve_detector_flags(
        scores_or_decisions,
        threshold=threshold,
        inclusive=inclusive,
        context="compute_recall",
    )

    tp = 0
    fn = 0
    for idx, (lbl, flagged) in enumerate(zip(clean_labels, flags, strict=True)):
        is_target = lbl == 1
        if eligible_mask is not None:
            is_target = is_target and bool(eligible_mask[idx])
        if is_target:
            if flagged:
                tp += 1
            else:
                fn += 1

    pos_total = tp + fn
    if pos_total == 0:
        raise ZeroDenominatorError(
            f"compute_recall: zero positive denominator samples for recall_kind='{recall_kind}'."
        )

    rate = float(tp) / float(pos_total)
    ci = wilson_ci(tp, pos_total, confidence=confidence)
    return RecallResult(
        tp=tp,
        fn=fn,
        positive_total=pos_total,
        recall=rate,
        recall_percent=rate * 100.0,
        wilson_ci=ci,
        recall_kind=recall_kind,
        threshold=float(threshold) if threshold is not None else None,
        inclusive=inclusive,
    )


@dataclass(frozen=True)
class LockedOperatingPointResult:
    """Evaluation result at a D1 benign-calibrated locked threshold (Task 14.11)."""

    locked_threshold: float
    target_fpr: float
    cal_sample_count: int
    recall: RecallResult
    eval_fpr: FPRResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "locked_threshold": self.locked_threshold,
            "target_fpr": self.target_fpr,
            "cal_sample_count": self.cal_sample_count,
            "recall": self.recall.to_dict(),
            "eval_fpr": self.eval_fpr.to_dict(),
        }


def compute_recall_at_locked_fpr(
    cal_benign_scores: Sequence[float],
    eval_labels: Sequence[int],
    eval_scores: Sequence[float],
    *,
    target_fpr: float = 0.01,
    inclusive: bool = True,
    eligible_mask: Sequence[bool] | None = None,
    recall_kind: str = "triggered_malware",
    cal_sample_ids: Sequence[str] | None = None,
    eval_sample_ids: Sequence[str] | None = None,
    confidence: float = 0.95,
) -> LockedOperatingPointResult:
    """Locks threshold on independent D1 benign calibration set, then evaluates Recall & FPR."""
    if not (0.0 < target_fpr < 1.0):
        raise MetricError(f"target_fpr must be in (0, 1), got {target_fpr}.")
    clean_cal = _validate_finite_scores(
        cal_benign_scores, context="compute_recall_at_locked_fpr[cal]"
    )
    if len(clean_cal) < 10:
        raise MetricError("At least 10 calibration benign scores are required to lock threshold.")

    if cal_sample_ids is not None:
        if len(cal_sample_ids) != len(clean_cal):
            raise MetricError("cal_sample_ids length must match cal_benign_scores length.")
        validate_unique_sample_ids(cal_sample_ids, context="cal_sample_ids")
    if eval_sample_ids is not None:
        if len(eval_sample_ids) != len(eval_labels):
            raise MetricError("eval_sample_ids length must match eval_labels length.")
        validate_unique_sample_ids(eval_sample_ids, context="eval_sample_ids")
    if cal_sample_ids is not None and eval_sample_ids is not None:
        overlap = set(cal_sample_ids).intersection(set(eval_sample_ids))
        if overlap:
            raise EvaluationLeakageError(
                f"Calibration and evaluation sample IDs overlap "
                f"({len(overlap)} shared IDs, e.g. {sorted(overlap)[0]})."
            )

    sorted_cal = sorted(clean_cal)
    n_cal = len(sorted_cal)
    allowed_fps = int(math.floor(target_fpr * n_cal))
    rank_index = n_cal - allowed_fps
    threshold_idx = min(max(0, rank_index), n_cal - 1)
    locked_threshold = float(sorted_cal[threshold_idx])

    recall_res = compute_recall(
        eval_labels,
        eval_scores,
        threshold=locked_threshold,
        inclusive=inclusive,
        eligible_mask=eligible_mask,
        recall_kind=recall_kind,
        confidence=confidence,
        sample_ids=eval_sample_ids,
    )
    fpr_res = compute_fpr(
        eval_labels,
        eval_scores,
        threshold=locked_threshold,
        inclusive=inclusive,
        confidence=confidence,
        sample_ids=eval_sample_ids,
    )
    return LockedOperatingPointResult(
        locked_threshold=locked_threshold,
        target_fpr=target_fpr,
        cal_sample_count=len(clean_cal),
        recall=recall_res,
        eval_fpr=fpr_res,
    )


@dataclass(frozen=True)
class ASRResult:
    """Pre-defense ASR, Clean-Trigger Control, and Post-Defense ASR result (Task 14.11)."""

    total_malware_count: int
    eligible_count: int
    successful_attack_count: int
    asr: float
    asr_percent: float
    asr_wilson_ci: WilsonCIResult
    clean_trigger_evasion_count: int | None
    clean_trigger_evasion_rate: float | None
    poisoning_associated_gain: float | None
    post_defense_undefeated_count: int | None
    post_defense_asr: float | None
    post_defense_asr_wilson_ci: WilsonCIResult | None
    eligible_sample_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_malware_count": self.total_malware_count,
            "eligible_count": self.eligible_count,
            "successful_attack_count": self.successful_attack_count,
            "asr": self.asr,
            "asr_percent": self.asr_percent,
            "asr_wilson_ci": self.asr_wilson_ci.to_dict(),
            "clean_trigger_evasion_count": self.clean_trigger_evasion_count,
            "clean_trigger_evasion_rate": self.clean_trigger_evasion_rate,
            "poisoning_associated_gain": self.poisoning_associated_gain,
            "post_defense_undefeated_count": self.post_defense_undefeated_count,
            "post_defense_asr": self.post_defense_asr,
            "post_defense_asr_wilson_ci": (
                self.post_defense_asr_wilson_ci.to_dict()
                if self.post_defense_asr_wilson_ci is not None
                else None
            ),
            "eligible_sample_ids": list(self.eligible_sample_ids),
        }


def compute_asr(
    is_malware: Sequence[int],
    clean_model_scores: Sequence[float],
    poisoned_triggered_scores: Sequence[float],
    *,
    malware_threshold: float = 0.50,
    clean_triggered_scores: Sequence[float] | None = None,
    detector_decisions_or_scores: Sequence[float | str] | None = None,
    detector_threshold: float | None = None,
    detector_inclusive: bool = True,
    sample_ids: Sequence[str] | None = None,
    confidence: float = 0.95,
) -> ASRResult:
    """Computes Pre-Defense ASR, Clean-Trigger Control Evasion, and Post-Defense ASR."""
    clean_mal_flags = _validate_binary_labels(is_malware, context="compute_asr[is_malware]")
    n_total = len(clean_mal_flags)
    if len(clean_model_scores) != n_total or len(poisoned_triggered_scores) != n_total:
        raise MetricError("compute_asr: input sequences must have equal length.")

    clean_s = _validate_finite_scores(clean_model_scores, context="compute_asr[clean_model_scores]")
    pois_trig_s = _validate_finite_scores(
        poisoned_triggered_scores, context="compute_asr[poisoned_triggered_scores]"
    )

    if sample_ids is not None:
        if len(sample_ids) != n_total:
            raise MetricError("compute_asr: sample_ids length mismatch.")
        s_ids = validate_unique_sample_ids(sample_ids, context="compute_asr")
    else:
        s_ids = [f"sample_{i}" for i in range(n_total)]

    clean_trig_s: list[float] | None = None
    if clean_triggered_scores is not None:
        if len(clean_triggered_scores) != n_total:
            raise MetricError("compute_asr: clean_triggered_scores length mismatch.")
        clean_trig_s = _validate_finite_scores(
            clean_triggered_scores, context="compute_asr[clean_triggered_scores]"
        )

    det_flags: list[bool] | None = None
    if detector_decisions_or_scores is not None:
        if len(detector_decisions_or_scores) != n_total:
            raise MetricError("compute_asr: detector_decisions_or_scores length mismatch.")
        det_flags = _resolve_detector_flags(
            detector_decisions_or_scores,
            threshold=detector_threshold,
            inclusive=detector_inclusive,
            context="compute_asr[detector]",
        )

    total_malware = sum(1 for m in clean_mal_flags if m == 1)
    eligible_indices: list[int] = []
    for idx, (mal, c_score) in enumerate(zip(clean_mal_flags, clean_s, strict=True)):
        if mal == 1 and c_score >= malware_threshold:
            eligible_indices.append(idx)

    eligible_count = len(eligible_indices)
    if eligible_count == 0:
        raise ZeroEligibleSamplesError(
            "Zero eligible malware samples found "
            f"(total_malware={total_malware}, malware_threshold={malware_threshold})."
        )

    succ_count = sum(1 for idx in eligible_indices if pois_trig_s[idx] < malware_threshold)
    asr_val = attack_success_rate(succ_count, eligible_count)
    asr_ci = wilson_ci(succ_count, eligible_count, confidence=confidence)

    ctrl_count: int | None = None
    ctrl_rate: float | None = None
    gain: float | None = None
    if clean_trig_s is not None:
        ctrl_count = sum(1 for idx in eligible_indices if clean_trig_s[idx] < malware_threshold)
        ctrl_rate = float(ctrl_count) / float(eligible_count)
        gain = asr_val - ctrl_rate

    post_def_count: int | None = None
    post_def_asr: float | None = None
    post_def_ci: WilsonCIResult | None = None
    if det_flags is not None:
        post_def_count = sum(
            1
            for idx in eligible_indices
            if (pois_trig_s[idx] < malware_threshold) and (not det_flags[idx])
        )
        post_def_asr = float(post_def_count) / float(eligible_count)
        post_def_ci = wilson_ci(post_def_count, eligible_count, confidence=confidence)

    return ASRResult(
        total_malware_count=total_malware,
        eligible_count=eligible_count,
        successful_attack_count=succ_count,
        asr=asr_val,
        asr_percent=asr_val * 100.0,
        asr_wilson_ci=asr_ci,
        clean_trigger_evasion_count=ctrl_count,
        clean_trigger_evasion_rate=ctrl_rate,
        poisoning_associated_gain=gain,
        post_defense_undefeated_count=post_def_count,
        post_defense_asr=post_def_asr,
        post_defense_asr_wilson_ci=post_def_ci,
        eligible_sample_ids=tuple(s_ids[idx] for idx in eligible_indices),
    )


@dataclass(frozen=True)
class LatencySummary:
    """Scoped latency summary with p50, p95, p99 percentiles in milliseconds (Task 14.10/14.11)."""

    scope: str
    count: int
    warmup_count: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "count": self.count,
            "warmup_count": self.warmup_count,
            "mean_ms": self.mean_ms,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
        }


def compute_latency_summary(
    durations_ms: Sequence[float],
    *,
    scope: str = "detector_only",
    warmup_count: int = 0,
) -> LatencySummary:
    """Computes mean, p50, p95, p99 latency statistics for an explicitly named scope."""
    if scope not in ALLOWED_LATENCY_SCOPES:
        raise ValueError(
            f"Unsupported latency scope '{scope}'. Must be one of {sorted(ALLOWED_LATENCY_SCOPES)}."
        )
    if warmup_count < 0:
        raise ValueError(f"warmup_count must be >= 0, got {warmup_count}.")
    clean_vals = _validate_finite_scores(durations_ms, context="compute_latency_summary")
    if any(v < 0.0 for v in clean_vals):
        raise ValueError("Latency durations must be non-negative.")

    arr = np.asarray(clean_vals, dtype=np.float64)
    return LatencySummary(
        scope=scope,
        count=len(clean_vals),
        warmup_count=warmup_count,
        mean_ms=float(np.mean(arr)),
        p50_ms=float(np.percentile(arr, 50)),
        p95_ms=float(np.percentile(arr, 95)),
        p99_ms=float(np.percentile(arr, 99)),
        min_ms=float(np.min(arr)),
        max_ms=float(np.max(arr)),
    )
