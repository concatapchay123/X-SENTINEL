from __future__ import annotations

import math
import time
from types import TracebackType


class PreciseTimer:
    """High-precision monotonic timer using time.perf_counter_ns().

    Guarantees:
    - Nanosecond precision converted cleanly to milliseconds.
    - Monotonic: non-negative durations strictly enforced.
    - Robust exception handling: captures exception paths without discarding elapsed time.
    """

    def __init__(self, name: str = "operation") -> None:
        self.name = name
        self.start_ns: int = 0
        self.end_ns: int = 0
        self.elapsed_ns: int = 0
        self.has_error: bool = False
        self.error_type: str | None = None
        self._is_running: bool = False

    def start(self) -> PreciseTimer:
        self.start_ns = time.perf_counter_ns()
        self.end_ns = 0
        self.elapsed_ns = 0
        self.has_error = False
        self.error_type = None
        self._is_running = True
        return self

    def stop(self, error: BaseException | None = None) -> float:
        stop_ns = time.perf_counter_ns()
        if not self._is_running:
            return self.elapsed_ms

        self.end_ns = stop_ns
        self._is_running = False
        self.elapsed_ns = max(0, self.end_ns - self.start_ns)

        if error is not None:
            self.has_error = True
            self.error_type = type(error).__name__

        return self.elapsed_ms

    @property
    def elapsed_ms(self) -> float:
        if self._is_running:
            current_ns = time.perf_counter_ns()
            return max(0.0, (current_ns - self.start_ns) / 1_000_000.0)
        return max(0.0, self.elapsed_ns / 1_000_000.0)

    def __enter__(self) -> PreciseTimer:
        return self.start()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stop(error=exc_val)


class TimingCollector:
    """Collects and organizes fine-grained, non-overlapping or sequential stage timings.

    Guarantees:
    - High-precision recording for each stage.
    - Zero double-counting.
    - Clean dictionary export for CanonicalEvidence and telemetry.
    """

    def __init__(self, root_name: str = "total") -> None:
        self.root_name = root_name
        self.root_timer = PreciseTimer(root_name)
        self._stage_timings: dict[str, float] = {}
        self._active_timers: dict[str, PreciseTimer] = {}
        self._stage_errors: dict[str, str] = {}

    def start(self) -> TimingCollector:
        self.root_timer.start()
        return self

    def stop(self, error: BaseException | None = None) -> float:
        for stage_name, timer in list(self._active_timers.items()):
            elapsed = timer.stop(error=error)
            self._stage_timings[stage_name] = round(elapsed, 4)
            if timer.has_error and timer.error_type:
                self._stage_errors[stage_name] = timer.error_type
        self._active_timers.clear()
        return self.root_timer.stop(error=error)

    def start_stage(self, name: str) -> None:
        clean_name = str(name).strip()
        timer = PreciseTimer(clean_name).start()
        self._active_timers[clean_name] = timer

    def stop_stage(self, name: str, error: BaseException | None = None) -> float:
        clean_name = str(name).strip()
        timer = self._active_timers.pop(clean_name, None)
        if timer is None:
            return self._stage_timings.get(clean_name, 0.0)
        elapsed = timer.stop(error=error)
        rounded = round(elapsed, 4)
        self._stage_timings[clean_name] = rounded
        if timer.has_error and timer.error_type:
            self._stage_errors[clean_name] = timer.error_type
        return rounded

    def stage(self, name: str) -> _StageContext:
        return _StageContext(self, name)

    @property
    def total_ms(self) -> float:
        return round(self.root_timer.elapsed_ms, 4)

    def to_dict(self, include_total_as: str = "end_to_end") -> dict[str, float]:
        res: dict[str, float] = {}
        if include_total_as:
            res[include_total_as] = self.total_ms
        for k, v in self._stage_timings.items():
            if math.isfinite(v) and v >= 0.0:
                res[k] = v
            else:
                res[k] = 0.0
        return res

    def __enter__(self) -> TimingCollector:
        return self.start()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stop(error=exc_val)


class _StageContext:
    def __init__(self, collector: TimingCollector, stage_name: str) -> None:
        self.collector = collector
        self.stage_name = stage_name

    def __enter__(self) -> _StageContext:
        self.collector.start_stage(self.stage_name)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.collector.stop_stage(self.stage_name, error=exc_val)
