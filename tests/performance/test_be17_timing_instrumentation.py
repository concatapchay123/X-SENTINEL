from __future__ import annotations

import math
import time

import pytest

from infrastructure.monitoring.timer import PreciseTimer, TimingCollector


class TestPreciseTimer:
    def test_timer_measures_positive_elapsed_duration(self) -> None:
        timer = PreciseTimer("test_op")
        with timer:
            time.sleep(0.01)  # 10ms

        assert timer.elapsed_ms > 5.0
        assert timer.elapsed_ns > 5_000_000
        assert math.isfinite(timer.elapsed_ms)
        assert timer.has_error is False
        assert timer.error_type is None

    def test_timer_captures_exception_without_discarding_elapsed(self) -> None:
        timer = PreciseTimer("error_op")
        with pytest.raises(ValueError, match="simulated failure"):
            with timer:
                time.sleep(0.005)
                raise ValueError("simulated failure")

        assert timer.elapsed_ms > 1.0
        assert timer.has_error is True
        assert timer.error_type == "ValueError"

    def test_timer_non_negative_monotonicity(self) -> None:
        timer = PreciseTimer("fast_op")
        with timer:
            pass  # instant operation

        assert timer.elapsed_ms >= 0.0
        assert timer.elapsed_ns >= 0

    def test_timer_manual_start_stop(self) -> None:
        timer = PreciseTimer("manual")
        timer.start()
        time.sleep(0.005)
        elapsed = timer.stop()

        assert elapsed > 1.0
        assert timer.elapsed_ms == elapsed


class TestTimingCollector:
    def test_sequential_stages_no_double_counting(self) -> None:
        collector = TimingCollector("detector_pipeline").start()

        with collector.stage("input_validation"):
            time.sleep(0.005)

        with collector.stage("model_inference"):
            time.sleep(0.010)

        with collector.stage("fusion"):
            time.sleep(0.005)

        collector.stop()

        timings = collector.to_dict(include_total_as="end_to_end")

        assert "end_to_end" in timings
        assert "input_validation" in timings
        assert "model_inference" in timings
        assert "fusion" in timings

        assert timings["input_validation"] > 2.0
        assert timings["model_inference"] > 5.0
        assert timings["fusion"] > 2.0

        # Sum of stages must be less than or approximately equal to end-to-end total
        stage_sum = (
            timings["input_validation"]
            + timings["model_inference"]
            + timings["fusion"]
        )
        assert stage_sum <= timings["end_to_end"] + 1.0

    def test_stage_exception_recording(self) -> None:
        collector = TimingCollector("resilient").start()

        with pytest.raises(RuntimeError):
            with collector.stage("failing_stage"):
                time.sleep(0.005)
                raise RuntimeError("stage exploded")

        collector.stop()
        timings = collector.to_dict(include_total_as="end_to_end")

        assert "failing_stage" in timings
        assert timings["failing_stage"] > 1.0
        assert timings["end_to_end"] >= timings["failing_stage"]

    def test_timing_collector_all_values_finite_and_non_negative(self) -> None:
        collector = TimingCollector("clean_check")
        with collector:
            with collector.stage("fast1"):
                pass
            with collector.stage("fast2"):
                pass

        data = collector.to_dict(include_total_as="end_to_end")
        for _k, v in data.items():
            assert isinstance(v, float)
            assert math.isfinite(v)
            assert v >= 0.0
