from __future__ import annotations

import pytest

from infrastructure.monitoring.percentiles import (
    BenchmarkSummary,
    PercentileCalculationError,
    calculate_percentiles,
    validate_duration_samples,
)


class TestPercentileCalculations:
    def test_calculate_percentiles_known_distribution(self) -> None:
        # 100 samples uniformly spaced from 1.0 to 100.0
        samples = [float(i) for i in range(1, 101)]
        res = calculate_percentiles(samples, percentiles=(50.0, 95.0, 99.0))

        assert res[50.0] == pytest.approx(50.5, abs=0.1)
        assert res[95.0] == pytest.approx(95.05, abs=0.1)
        assert res[99.0] == pytest.approx(99.01, abs=0.1)

    def test_empty_samples_rejected(self) -> None:
        with pytest.raises(PercentileCalculationError, match="cannot be empty"):
            calculate_percentiles([])

    def test_single_sample_handling(self) -> None:
        res = calculate_percentiles([42.5], percentiles=(50.0, 95.0, 99.0))
        assert res[50.0] == 42.5
        assert res[95.0] == 42.5
        assert res[99.0] == 42.5

    def test_unsorted_samples_invariant(self) -> None:
        sorted_samples = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        shuffled_samples = [8.0, 1.0, 10.0, 3.0, 2.0, 7.0, 4.0, 6.0, 5.0, 9.0]

        res_sorted = calculate_percentiles(sorted_samples)
        res_shuffled = calculate_percentiles(shuffled_samples)

        assert res_sorted == res_shuffled

    def test_identical_samples(self) -> None:
        samples = [10.0] * 50
        res = calculate_percentiles(samples)

        assert res[50.0] == 10.0
        assert res[95.0] == 10.0
        assert res[99.0] == 10.0

    def test_extreme_tail_latency_capture(self) -> None:
        # 98 fast samples of 5.0ms, 2 outlier samples of 500.0ms (so top 2% are 500ms)
        samples = [5.0] * 98 + [500.0, 500.0]
        res = calculate_percentiles(samples)

        assert res[50.0] == 5.0
        # P95 should still be low
        assert res[95.0] == pytest.approx(5.0, abs=0.5)
        # P99 captures the extreme tail
        assert res[99.0] > 50.0

    def test_negative_and_non_finite_rejection(self) -> None:
        with pytest.raises(PercentileCalculationError, match="negative"):
            validate_duration_samples([1.0, -0.5, 3.0])

        with pytest.raises(PercentileCalculationError, match="non-finite"):
            validate_duration_samples([1.0, float("nan"), 3.0])

        with pytest.raises(PercentileCalculationError, match="non-finite"):
            validate_duration_samples([1.0, float("inf"), 3.0])

        with pytest.raises(PercentileCalculationError, match="non-numeric"):
            validate_duration_samples([1.0, True, 3.0])  # type: ignore[list-item]


class TestBenchmarkSummary:
    def test_summary_creation_and_warnings(self) -> None:
        # Small sample size (N=20 < 30)
        samples = [float(i) for i in range(1, 21)]
        summary = BenchmarkSummary.from_samples(
            samples,
            component="detector",
            workload="ember_2381",
            warmup_count=3,
            failures=1,
            timeouts=0,
            total_test_duration_s=0.5,
        )

        assert summary.component == "detector"
        assert summary.sample_count == 20
        assert summary.warmup_count == 3
        assert summary.failure_count == 1
        assert summary.error_rate == pytest.approx(1.0 / 21.0, abs=1e-4)
        assert summary.p50_ms == pytest.approx(10.5, abs=0.5)
        assert summary.throughput_ops_per_sec == 40.0
        assert len(summary.warnings) > 0
        assert any("N=20 < 30" in w for w in summary.warnings)

        data = summary.to_dict()
        assert data["component"] == "detector"
        assert "p50_ms" in data
        assert "p95_ms" in data
        assert "p99_ms" in data

    def test_summary_large_sample_size_no_small_warnings(self) -> None:
        samples = [5.0] * 120
        summary = BenchmarkSummary.from_samples(samples, component="jev_ai")
        assert len(summary.warnings) == 0
        assert summary.sample_count == 120
