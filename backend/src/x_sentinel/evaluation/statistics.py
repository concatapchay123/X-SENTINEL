from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import binomtest, chi2, norm

from x_sentinel.fusion.calibration import wilson_score_interval


class DuplicateSampleIDError(ValueError):
    """Raised when duplicate sample_ids violate sample-level independence or pairing."""


def validate_unique_sample_ids(sample_ids: Sequence[str], context: str = "evaluation") -> list[str]:
    """Validates that all sample_ids are non-empty unique strings."""
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw_id in sample_ids:
        if not isinstance(raw_id, str) or not raw_id.strip():
            raise ValueError(f"Invalid empty or non-string sample_id in {context}: {raw_id!r}.")
        if raw_id in seen:
            raise DuplicateSampleIDError(f"Duplicate sample_id '{raw_id}' detected in {context}.")
        seen.add(raw_id)
        cleaned.append(raw_id)
    return cleaned


@dataclass(frozen=True)
class WilsonCIResult:
    """Result of Wilson score binomial confidence interval calculation (Task 14.12)."""

    k: int
    n: int
    p_hat: float
    lower: float
    upper: float
    confidence: float
    z_value: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "k": self.k,
            "n": self.n,
            "p_hat": self.p_hat,
            "lower": self.lower,
            "upper": self.upper,
            "confidence": self.confidence,
            "z_value": self.z_value,
        }


def wilson_ci(
    k: int,
    n: int,
    confidence: float = 0.95,
) -> WilsonCIResult:
    """Computes the Wilson score confidence interval for k successes in n trials."""
    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError(f"k must be an integer (not bool/float), got {type(k).__name__}.")
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"n must be an integer (not bool/float), got {type(n).__name__}.")
    if n <= 0:
        raise ValueError(f"n must be a strictly positive integer, got {n}.")
    if not (0 <= k <= n):
        raise ValueError(f"k must be in [0, {n}], got {k}.")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(float(confidence))
        or not (0.0 < float(confidence) < 1.0)
    ):
        raise ValueError(f"confidence must be a finite float in (0, 1), got {confidence!r}.")

    conf = float(confidence)
    if abs(conf - 0.95) < 1e-4:
        z = 1.959963984540054
    elif abs(conf - 0.99) < 1e-4:
        z = 2.5758293035489004
    elif abs(conf - 0.90) < 1e-4:
        z = 1.6448536269514722
    else:
        z = float(norm.ppf(1.0 - (1.0 - conf) / 2.0))

    lower, upper = wilson_score_interval(k, n, confidence=conf)
    return WilsonCIResult(
        k=k,
        n=n,
        p_hat=float(k) / float(n),
        lower=lower,
        upper=upper,
        confidence=conf,
        z_value=z,
    )


def align_paired_records(
    records_a: Sequence[dict[str, Any]],
    records_b: Sequence[dict[str, Any]],
    *,
    id_key: str = "sample_id",
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Aligns two sequences of sample records strictly by sample_id (never by row order)."""
    if len(records_a) == 0 or len(records_b) == 0:
        raise ValueError("Cannot align empty record sequences.")

    ids_a = [str(r.get(id_key, "")) for r in records_a]
    ids_b = [str(r.get(id_key, "")) for r in records_b]
    validate_unique_sample_ids(ids_a, context="records_a")
    validate_unique_sample_ids(ids_b, context="records_b")

    map_b = {str(r[id_key]): r for r in records_b}
    set_a = set(ids_a)
    set_b = set(ids_b)
    if set_a != set_b:
        missing_in_b = sorted(set_a - set_b)
        missing_in_a = sorted(set_b - set_a)
        raise ValueError(
            f"Mismatched sample IDs between paired runs: "
            f"missing_in_b={missing_in_b[:5]}, missing_in_a={missing_in_a[:5]}."
        )

    return [(rec_a, map_b[str(rec_a[id_key])]) for rec_a in records_a]


@dataclass(frozen=True)
class McNemarResult:
    """Paired 2x2 concordance and McNemar significance result (Task 14.13)."""

    both_positive: int
    a_only: int
    b_only: int
    neither: int
    total_pairs: int
    statistic: float
    p_value: float
    exact: bool
    method: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "both_positive": self.both_positive,
            "a_only": self.a_only,
            "b_only": self.b_only,
            "neither": self.neither,
            "total_pairs": self.total_pairs,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "exact": self.exact,
            "method": self.method,
        }


def mcnemar_paired_test(
    outcomes_a: Sequence[int],
    outcomes_b: Sequence[int],
    *,
    sample_ids: Sequence[str] | None = None,
    exact: bool | None = None,
) -> McNemarResult:
    """Computes paired McNemar test on binary detection/classification outcomes."""
    if len(outcomes_a) == 0:
        raise ValueError("outcomes_a cannot be empty.")
    if len(outcomes_a) != len(outcomes_b):
        raise ValueError(
            f"outcomes_a length ({len(outcomes_a)}) != outcomes_b length ({len(outcomes_b)})."
        )
    if sample_ids is not None:
        if len(sample_ids) != len(outcomes_a):
            raise ValueError("sample_ids length must match outcomes_a length.")
        validate_unique_sample_ids(sample_ids, context="mcnemar_paired_test")

    both_pos = 0
    a_only = 0
    b_only = 0
    neither = 0

    for a, b in zip(outcomes_a, outcomes_b, strict=True):
        if isinstance(a, bool) or not isinstance(a, int) or a not in (0, 1):
            raise ValueError(f"outcomes_a must contain binary integers in {{0, 1}}, got {a!r}.")
        if isinstance(b, bool) or not isinstance(b, int) or b not in (0, 1):
            raise ValueError(f"outcomes_b must contain binary integers in {{0, 1}}, got {b!r}.")
        if a == 1 and b == 1:
            both_pos += 1
        elif a == 1 and b == 0:
            a_only += 1
        elif a == 0 and b == 1:
            b_only += 1
        else:
            neither += 1

    total = len(outcomes_a)
    discordant = a_only + b_only
    use_exact = (discordant < 25) if exact is None else bool(exact)

    if discordant == 0:
        return McNemarResult(
            both_positive=both_pos,
            a_only=0,
            b_only=0,
            neither=neither,
            total_pairs=total,
            statistic=0.0,
            p_value=1.0,
            exact=use_exact,
            method="mcnemar_exact_binomial" if use_exact else "mcnemar_chi2_cc",
        )

    stat_cc = float((max(0.0, abs(a_only - b_only) - 1.0) ** 2) / float(discordant))
    if use_exact:
        p_val = float(binomtest(a_only, n=discordant, p=0.5, alternative="two-sided").pvalue)
        method_name = "mcnemar_exact_binomial"
    else:
        p_val = float(chi2.sf(stat_cc, df=1))
        method_name = "mcnemar_chi2_cc"

    return McNemarResult(
        both_positive=both_pos,
        a_only=a_only,
        b_only=b_only,
        neither=neither,
        total_pairs=total,
        statistic=stat_cc,
        p_value=min(1.0, max(0.0, p_val)),
        exact=use_exact,
        method=method_name,
    )


@dataclass(frozen=True)
class PairedBootstrapResult:
    """Result of paired or cluster-paired bootstrap difference test (Task 14.13)."""

    observed_diff: float
    ci_low: float
    ci_high: float
    p_value: float
    confidence: float
    n_boot: int
    n_observations: int
    n_clusters: int
    is_clustered: bool
    seed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_diff": self.observed_diff,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "p_value": self.p_value,
            "confidence": self.confidence,
            "n_boot": self.n_boot,
            "n_observations": self.n_observations,
            "n_clusters": self.n_clusters,
            "is_clustered": self.is_clustered,
            "seed": self.seed,
        }


def paired_bootstrap_test(
    values_a: Sequence[float],
    values_b: Sequence[float],
    *,
    sample_ids: Sequence[str] | None = None,
    cluster_ids: Sequence[str] | None = None,
    n_boot: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> PairedBootstrapResult:
    """Computes paired or cluster-paired bootstrap CI and two-sided p-value for mean(A - B)."""
    n_obs = len(values_a)
    if n_obs < 2:
        raise ValueError(f"At least 2 paired observations are required, got {n_obs}.")
    if len(values_b) != n_obs:
        raise ValueError(f"values_a length ({n_obs}) != values_b length ({len(values_b)}).")
    if n_boot < 50:
        raise ValueError(f"n_boot must be >= 50, got {n_boot}.")
    if not (0.0 < confidence < 1.0):
        raise ValueError(f"confidence must be in (0, 1), got {confidence}.")

    if sample_ids is not None:
        if len(sample_ids) != n_obs:
            raise ValueError("sample_ids length must match values_a length.")
        validate_unique_sample_ids(sample_ids, context="paired_bootstrap_test")

    arr_a = np.asarray(values_a, dtype=np.float64)
    arr_b = np.asarray(values_b, dtype=np.float64)
    if not (np.all(np.isfinite(arr_a)) and np.all(np.isfinite(arr_b))):
        raise ValueError("values_a and values_b must contain only finite numbers.")

    diffs = arr_a - arr_b
    observed_diff = float(np.mean(diffs))
    rng = np.random.default_rng(seed)

    if cluster_ids is not None:
        if len(cluster_ids) != n_obs:
            raise ValueError("cluster_ids length must match values_a length.")
        cluster_order: list[str] = []
        cluster_map: dict[str, list[int]] = {}
        for idx, cid in enumerate(cluster_ids):
            if not isinstance(cid, str) or not cid.strip():
                raise ValueError(f"Invalid cluster_id at index {idx}: {cid!r}.")
            if cid not in cluster_map:
                cluster_order.append(cid)
                cluster_map[cid] = []
            cluster_map[cid].append(idx)
        n_clusters = len(cluster_order)
        is_clustered = n_clusters < n_obs
        if is_clustered:
            cluster_means = np.array(
                [float(np.mean(diffs[cluster_map[cid]])) for cid in cluster_order],
                dtype=np.float64,
            )
            boot_indices = rng.integers(0, n_clusters, size=(n_boot, n_clusters))
            boot_diffs = np.mean(cluster_means[boot_indices], axis=1)
        else:
            boot_indices = rng.integers(0, n_obs, size=(n_boot, n_obs))
            boot_diffs = np.mean(diffs[boot_indices], axis=1)
    else:
        n_clusters = n_obs
        is_clustered = False
        boot_indices = rng.integers(0, n_obs, size=(n_boot, n_obs))
        boot_diffs = np.mean(diffs[boot_indices], axis=1)

    alpha = 1.0 - confidence
    ci_low = float(np.quantile(boot_diffs, alpha / 2.0))
    ci_high = float(np.quantile(boot_diffs, 1.0 - alpha / 2.0))

    if np.allclose(diffs, 0.0):
        p_val = 1.0
    else:
        prop_le_zero = float(np.mean(boot_diffs <= 0.0))
        prop_ge_zero = float(np.mean(boot_diffs >= 0.0))
        p_val = min(1.0, 2.0 * min(prop_le_zero, prop_ge_zero))

    return PairedBootstrapResult(
        observed_diff=observed_diff,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_val,
        confidence=confidence,
        n_boot=n_boot,
        n_observations=n_obs,
        n_clusters=n_clusters,
        is_clustered=is_clustered,
        seed=seed,
    )


def _compute_midranks(x: np.ndarray) -> np.ndarray:
    """Computes 1-based midranks for ties (DeLong structural component helper)."""
    n = len(x)
    order = np.argsort(x, kind="mergesort")
    sorted_x = x[order]
    midranks_sorted = np.zeros(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i
        while j < n and sorted_x[j] == sorted_x[i]:
            j += 1
        midranks_sorted[i:j] = 0.5 * (i + 1 + j)
        i = j
    midranks = np.empty(n, dtype=np.float64)
    midranks[order] = midranks_sorted
    return midranks


def _delong_structural_components(
    pos_scores: np.ndarray,
    neg_scores: np.ndarray,
) -> tuple[float, np.ndarray, np.ndarray]:
    """Computes exact empirical AUROC and DeLong V10, V01 structural placement values."""
    m = len(pos_scores)
    n = len(neg_scores)
    pooled = np.concatenate([pos_scores, neg_scores])
    pooled_midranks = _compute_midranks(pooled)
    pos_midranks = _compute_midranks(pos_scores)
    neg_midranks = _compute_midranks(neg_scores)

    auroc = float((np.sum(pooled_midranks[:m]) - m * (m + 1) / 2.0) / (m * n))
    v10 = (pooled_midranks[:m] - pos_midranks) / float(n)
    v01 = 1.0 - (pooled_midranks[m:] - neg_midranks) / float(m)
    return auroc, v10, v01


@dataclass(frozen=True)
class PairedAUROCResult:
    """Result of paired correlated AUROC comparison via DeLong or Bootstrap (Task 14.13)."""

    auroc_a: float
    auroc_b: float
    delta_auroc: float
    ci_low: float
    ci_high: float
    z_or_t_stat: float
    p_value: float
    method: str
    confidence: float
    n_positive: int
    n_negative: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "auroc_a": self.auroc_a,
            "auroc_b": self.auroc_b,
            "delta_auroc": self.delta_auroc,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "z_or_t_stat": self.z_or_t_stat,
            "p_value": self.p_value,
            "method": self.method,
            "confidence": self.confidence,
            "n_positive": self.n_positive,
            "n_negative": self.n_negative,
        }


def paired_auroc_comparison(
    labels: Sequence[int],
    scores_a: Sequence[float],
    scores_b: Sequence[float],
    *,
    sample_ids: Sequence[str] | None = None,
    cluster_ids: Sequence[str] | None = None,
    method: str = "delong",
    confidence: float = 0.95,
    n_boot: int = 1000,
    seed: int = 42,
) -> PairedAUROCResult:
    """Compares two ROC curves evaluated on the exact same paired samples."""
    if len(labels) == 0:
        raise ValueError("labels cannot be empty.")
    if not (len(labels) == len(scores_a) == len(scores_b)):
        raise ValueError("labels, scores_a, and scores_b must have equal length.")
    if sample_ids is not None:
        if len(sample_ids) != len(labels):
            raise ValueError("sample_ids length must match labels length.")
        validate_unique_sample_ids(sample_ids, context="paired_auroc_comparison")
    if cluster_ids is not None:
        if len(cluster_ids) != len(labels):
            raise ValueError("cluster_ids length must match labels length.")
        for idx, cid in enumerate(cluster_ids):
            if not isinstance(cid, str) or not cid.strip():
                raise ValueError(f"Invalid cluster_id at index {idx}: {cid!r}.")

    for lbl in labels:
        if isinstance(lbl, bool) or not isinstance(lbl, int) or lbl not in (0, 1):
            raise ValueError(f"labels must be binary integers in {{0, 1}}, got {lbl!r}.")

    y = np.asarray(labels, dtype=np.int64)
    sa = np.asarray(scores_a, dtype=np.float64)
    sb = np.asarray(scores_b, dtype=np.float64)
    if not (np.all(np.isfinite(sa)) and np.all(np.isfinite(sb))):
        raise ValueError("scores_a and scores_b must be finite numbers.")

    pos_mask = y == 1
    neg_mask = y == 0
    m = int(np.sum(pos_mask))
    n = int(np.sum(neg_mask))
    if m < 2 or n < 2:
        raise ValueError(
            "Paired AUROC comparison requires at least 2 positive and 2 negative "
            f"samples (got pos={m}, neg={n})."
        )

    auc_a, v10_a, v01_a = _delong_structural_components(sa[pos_mask], sa[neg_mask])
    auc_b, v10_b, v01_b = _delong_structural_components(sb[pos_mask], sb[neg_mask])
    delta = float(auc_a - auc_b)
    z_crit = float(norm.ppf(1.0 - (1.0 - confidence) / 2.0))

    method_norm = method.strip().lower()
    if method_norm == "delong":
        if cluster_ids is not None:
            pos_indices = np.flatnonzero(pos_mask)
            neg_indices = np.flatnonzero(neg_mask)
            pos_clusters = [str(cluster_ids[int(i)]) for i in pos_indices]
            neg_clusters = [str(cluster_ids[int(i)]) for i in neg_indices]
            unique_pos_c = list(dict.fromkeys(pos_clusters))
            unique_neg_c = list(dict.fromkeys(neg_clusters))
            if len(unique_pos_c) >= 2 and len(unique_pos_c) < m:
                v10_a_c = np.array(
                    [
                        np.mean([v10_a[j] for j, c in enumerate(pos_clusters) if c == uc])
                        for uc in unique_pos_c
                    ],
                    dtype=np.float64,
                )
                v10_b_c = np.array(
                    [
                        np.mean([v10_b[j] for j, c in enumerate(pos_clusters) if c == uc])
                        for uc in unique_pos_c
                    ],
                    dtype=np.float64,
                )
                s10 = np.cov(np.vstack([v10_a_c, v10_b_c]), ddof=1)
                m_eff = float(len(unique_pos_c))
            else:
                s10 = np.cov(np.vstack([v10_a, v10_b]), ddof=1)
                m_eff = float(m)
            if len(unique_neg_c) >= 2 and len(unique_neg_c) < n:
                v01_a_c = np.array(
                    [
                        np.mean([v01_a[j] for j, c in enumerate(neg_clusters) if c == uc])
                        for uc in unique_neg_c
                    ],
                    dtype=np.float64,
                )
                v01_b_c = np.array(
                    [
                        np.mean([v01_b[j] for j, c in enumerate(neg_clusters) if c == uc])
                        for uc in unique_neg_c
                    ],
                    dtype=np.float64,
                )
                s01 = np.cov(np.vstack([v01_a_c, v01_b_c]), ddof=1)
                n_eff = float(len(unique_neg_c))
            else:
                s01 = np.cov(np.vstack([v01_a, v01_b]), ddof=1)
                n_eff = float(n)
        else:
            s10 = np.cov(np.vstack([v10_a, v10_b]), ddof=1)
            s01 = np.cov(np.vstack([v01_a, v01_b]), ddof=1)
            m_eff = float(m)
            n_eff = float(n)
        cov_matrix = (s10 / m_eff) + (s01 / n_eff)
        var_delta = float(cov_matrix[0, 0] + cov_matrix[1, 1] - 2.0 * cov_matrix[0, 1])
        var_delta = max(0.0, var_delta)
        if var_delta <= 1e-18:
            z_stat = 0.0
            p_val = 1.0 if abs(delta) <= 1e-12 else 0.0
            ci_low = delta
            ci_high = delta
        else:
            se = math.sqrt(var_delta)
            z_stat = delta / se
            p_val = float(2.0 * norm.sf(abs(z_stat)))
            ci_low = delta - z_crit * se
            ci_high = delta + z_crit * se
        return PairedAUROCResult(
            auroc_a=auc_a,
            auroc_b=auc_b,
            delta_auroc=delta,
            ci_low=ci_low,
            ci_high=ci_high,
            z_or_t_stat=z_stat,
            p_value=min(1.0, max(0.0, p_val)),
            method="delong",
            confidence=confidence,
            n_positive=m,
            n_negative=n,
        )

    if method_norm == "bootstrap":
        rng = np.random.default_rng(seed)
        pos_idx = np.flatnonzero(pos_mask)
        neg_idx = np.flatnonzero(neg_mask)
        boot_deltas = np.empty(n_boot, dtype=np.float64)
        for b_idx in range(n_boot):
            samp_pos = rng.choice(pos_idx, size=m, replace=True)
            samp_neg = rng.choice(neg_idx, size=n, replace=True)
            b_auc_a, _, _ = _delong_structural_components(sa[samp_pos], sa[samp_neg])
            b_auc_b, _, _ = _delong_structural_components(sb[samp_pos], sb[samp_neg])
            boot_deltas[b_idx] = b_auc_a - b_auc_b

        alpha = 1.0 - confidence
        ci_low = float(np.quantile(boot_deltas, alpha / 2.0))
        ci_high = float(np.quantile(boot_deltas, 1.0 - alpha / 2.0))
        se_boot = float(np.std(boot_deltas, ddof=1))
        z_stat = 0.0 if se_boot <= 1e-15 else delta / se_boot
        prop_le = float(np.mean(boot_deltas <= 0.0))
        prop_ge = float(np.mean(boot_deltas >= 0.0))
        p_val = 1.0 if np.allclose(boot_deltas, 0.0) else min(1.0, 2.0 * min(prop_le, prop_ge))
        return PairedAUROCResult(
            auroc_a=auc_a,
            auroc_b=auc_b,
            delta_auroc=delta,
            ci_low=ci_low,
            ci_high=ci_high,
            z_or_t_stat=z_stat,
            p_value=p_val,
            method="bootstrap",
            confidence=confidence,
            n_positive=m,
            n_negative=n,
        )

    raise ValueError(f"Unsupported paired AUROC method '{method}'. Use 'delong' or 'bootstrap'.")


@dataclass(frozen=True)
class MultipleComparisonResult:
    """Result of Holm-Bonferroni step-down family-wise error control (Task 14.13)."""

    method: str
    alpha: float
    raw_p_values: dict[str, float]
    adjusted_p_values: dict[str, float]
    rejected: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "alpha": self.alpha,
            "raw_p_values": self.raw_p_values,
            "adjusted_p_values": self.adjusted_p_values,
            "rejected": self.rejected,
        }


def holm_bonferroni_correction(
    p_values: Sequence[float],
    *,
    alpha: float = 0.05,
    hypothesis_ids: Sequence[str] | None = None,
) -> MultipleComparisonResult:
    """Applies step-down Holm-Bonferroni correction across a family of hypotheses."""
    k = len(p_values)
    if k == 0:
        raise ValueError("p_values cannot be empty.")
    if not (0.0 < alpha < 1.0):
        raise ValueError(f"alpha must be in (0, 1), got {alpha}.")

    if hypothesis_ids is None:
        h_ids = [f"H_{i + 1}" for i in range(k)]
    else:
        if len(hypothesis_ids) != k:
            raise ValueError("hypothesis_ids length must match p_values length.")
        h_ids = list(hypothesis_ids)
        if len(set(h_ids)) != k:
            raise ValueError("hypothesis_ids must be unique.")

    for p in p_values:
        if not math.isfinite(float(p)) or not (0.0 <= float(p) <= 1.0):
            raise ValueError(f"Each p-value must be in [0, 1], got {p!r}.")

    indexed = sorted(enumerate(float(p) for p in p_values), key=lambda item: item[1])
    adjusted_sorted = [0.0] * k
    rejected_sorted = [False] * k
    running_max = 0.0
    stop_rejecting = False

    for rank, (orig_idx, p_val) in enumerate(indexed):
        multiplier = k - rank
        adj = min(1.0, p_val * multiplier)
        running_max = max(running_max, adj)
        adjusted_sorted[orig_idx] = running_max
        if not stop_rejecting and running_max <= alpha:
            rejected_sorted[orig_idx] = True
        else:
            stop_rejecting = True
            rejected_sorted[orig_idx] = False

    raw_map = {h_ids[i]: float(p_values[i]) for i in range(k)}
    adj_map = {h_ids[i]: adjusted_sorted[i] for i in range(k)}
    rej_map = {h_ids[i]: rejected_sorted[i] for i in range(k)}

    return MultipleComparisonResult(
        method="holm-bonferroni",
        alpha=alpha,
        raw_p_values=raw_map,
        adjusted_p_values=adj_map,
        rejected=rej_map,
    )
