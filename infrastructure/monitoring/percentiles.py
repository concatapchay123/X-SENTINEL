from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np


class PercentileCalculationError(ValueError):
    """Raised when duration samples fail mathematical validation."""


def validate_duration_samples(samples: Sequence[float], context: str = "percentiles") -> list[float]:
    """Validates that a collection of durations contains finite, non-negative numbers."""
    if len(samples) == 0:
        raise PercentileCalculationError(f"{context}: samples collection cannot be empty.")
    out: list[float] = []
    for idx, s in enumerate(samples):
        if isinstance(s, bool) or not isinstance(s, (int, float, np.floating, np.integer)):
            raise PercentileCalculationError(f"{context}: non-numeric sample at index {idx}: {s!r}.")
        val = float(s)
        if not math.isfinite(val):
            raise PercentileCalculationError(
                f"{context}: non-finite sample (NaN/Inf) at index {idx}: {s!r}."
            )
        if val < 0.0:
            raise PercentileCalculationError(
                f"{context}: negative duration sample at index {idx}: {val}."
            )
        out.append(val)
    return out


def calculate_percentiles(
    durations_ms: Sequence[float],
    percentiles: Sequence[float] = (50.0, 95.0, 99.0),
    *,
    method: str = "linear",
    context: str = "calculate_percentiles",
) -> dict[float, float]:
    """Computes exact empirical percentiles from raw duration samples using numpy.percentile.

    Estimator method defaults to standard 'linear' interpolation.
    """
    clean_vals = validate_duration_samples(durations_ms, context=context)
    arr = np.asarray(clean_vals, dtype=np.float64)

    for p in percentiles:
        if isinstance(p, bool) or not isinstance(p, (int, float, np.floating, np.integer)):
            raise PercentileCalculationError(f"{context}: invalid percentile specifier {p!r}.")
        if not (0.0 <= float(p) <= 100.0):
            raise PercentileCalculationError(
                f"{context}: percentile must be in [0.0, 100.0], got {p}."
            )

    results: dict[float, float] = {}
    for p in percentiles:
        pct = float(p)
        val = float(np.percentile(arr, pct, method=cast(Any, method)))
        results[pct] = round(val, 4)
    return results


@dataclass(frozen=True)
class BenchmarkSummary:
    """Comprehensive statistical summary of actual benchmark measurements."""

    component: str
    workload: str
    sample_count: int
    warmup_count: int
    success_count: int
    failure_count: int
    timeout_count: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float
    throughput_ops_per_sec: float
    duration_seconds: float
    error_rate: float
    timeout_rate: float
    method: str = "numpy.percentile(linear)"
    raw_durations_ms: list[float] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_samples(
        cls,
        durations_ms: Sequence[float],
        *,
        component: str,
        workload: str = "standard",
        warmup_count: int = 0,
        failures: int = 0,
        timeouts: int = 0,
        total_test_duration_s: float | None = None,
        method: str = "linear",
    ) -> BenchmarkSummary:
        if len(durations_ms) == 0:
            raise PercentileCalculationError("Cannot create BenchmarkSummary from empty samples.")

        clean_samples = validate_duration_samples(durations_ms, context="BenchmarkSummary")
        arr = np.asarray(clean_samples, dtype=np.float64)
        n = len(clean_samples)
        pcts = calculate_percentiles(clean_samples, percentiles=(50.0, 95.0, 99.0), method=method)

        mean_val = float(np.mean(arr))
        min_val = float(np.min(arr))
        max_val = float(np.max(arr))
        std_val = float(np.std(arr))

        total_offered = n + failures
        err_rate = float(failures) / float(total_offered) if total_offered > 0 else 0.0
        to_rate = float(timeouts) / float(total_offered) if total_offered > 0 else 0.0

        if total_test_duration_s is not None and total_test_duration_s > 0:
            duration_s = float(total_test_duration_s)
        else:
            duration_s = sum(clean_samples) / 1000.0

        throughput = float(n) / duration_s if duration_s > 0 else 0.0

        warns: list[str] = []
        if n < 30:
            warns.append(f"Small sample size (N={n} < 30): P95 and P99 have high sampling variance.")
        elif n < 100:
            warns.append(f"Moderate sample size (N={n} < 100): P99 requires >= 100 samples for high confidence.")

        return cls(
            component=component,
            workload=workload,
            sample_count=n,
            warmup_count=warmup_count,
            success_count=n,
            failure_count=failures,
            timeout_count=timeouts,
            p50_ms=pcts[50.0],
            p95_ms=pcts[95.0],
            p99_ms=pcts[99.0],
            mean_ms=round(mean_val, 4),
            min_ms=round(min_val, 4),
            max_ms=round(max_val, 4),
            std_dev_ms=round(std_val, 4),
            throughput_ops_per_sec=round(throughput, 2),
            duration_seconds=round(duration_s, 4),
            error_rate=round(err_rate, 4),
            timeout_rate=round(to_rate, 4),
            method=f"numpy.percentile({method})",
            raw_durations_ms=list(clean_samples),
            warnings=warns,
        )

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "component": self.component,
            "workload": self.workload,
            "sample_count": self.sample_count,
            "warmup_count": self.warmup_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "timeout_count": self.timeout_count,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "mean_ms": self.mean_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "std_dev_ms": self.std_dev_ms,
            "throughput_ops_per_sec": self.throughput_ops_per_sec,
            "duration_seconds": self.duration_seconds,
            "error_rate": self.error_rate,
            "timeout_rate": self.timeout_rate,
            "method": self.method,
            "warnings": self.warnings,
        }
        if include_raw:
            data["raw_durations_ms"] = self.raw_durations_ms
        return data
