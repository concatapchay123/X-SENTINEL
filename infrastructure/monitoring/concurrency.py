from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from types import TracebackType

logger = logging.getLogger("x_sentinel.monitoring.concurrency")


class ConcurrencyLimitExceededError(RuntimeError):
    """Raised when request volume exceeds concurrency limits or queue capacity."""

    def __init__(
        self,
        message: str,
        *,
        component: str,
        reason: str,
        current_in_flight: int,
        max_allowed: int,
    ) -> None:
        super().__init__(message)
        self.component = component
        self.reason = reason
        self.current_in_flight = current_in_flight
        self.max_allowed = max_allowed


@dataclass(frozen=True)
class ConcurrencyBudget:
    max_concurrent: int
    queue_capacity: int = 0
    queue_timeout_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.max_concurrent <= 0:
            raise ValueError(f"max_concurrent must be > 0; got {self.max_concurrent}")
        if self.queue_capacity < 0:
            raise ValueError(f"queue_capacity must be >= 0; got {self.queue_capacity}")
        if self.queue_timeout_seconds < 0.0:
            raise ValueError(
                f"queue_timeout_seconds must be >= 0.0; got {self.queue_timeout_seconds}"
            )


class ConcurrencyLimiter:
    """Thread-safe bounded concurrency limiter with queue capacity and wait timeouts.

    Protects critical system components (such as the Detector) against resource starvation,
    saturating load, and unconstrained parallel requests.
    """

    def __init__(self, component: str, budget: ConcurrencyBudget) -> None:
        self.component = component
        self.budget = budget
        self._lock = threading.Lock()
        self._in_flight = 0
        self._queue_waiters = 0
        self._semaphore = threading.Semaphore(budget.max_concurrent)
        self._total_requests = 0
        self._total_acquired = 0
        self._total_rejected = 0
        self._total_timeouts = 0

    @property
    def in_flight(self) -> int:
        with self._lock:
            return self._in_flight

    @property
    def queue_waiters(self) -> int:
        with self._lock:
            return self._queue_waiters

    def acquire(self, timeout: float | None = None) -> _LimiterContext:
        """Acquires a concurrency execution permit.

        Raises:
            ConcurrencyLimitExceededError: if queue is full or wait timeout is exceeded.
        """
        eff_timeout = self.budget.queue_timeout_seconds if timeout is None else float(timeout)

        with self._lock:
            self._total_requests += 1

            # Fast path: slot is available under limit
            if self._in_flight < self.budget.max_concurrent:
                acquired = self._semaphore.acquire(blocking=False)
                if acquired:
                    self._in_flight += 1
                    self._total_acquired += 1
                    self._update_metrics()
                    return _LimiterContext(self)

            # All concurrency slots are full; check queue capacity
            if self.budget.queue_capacity <= 0 or self._queue_waiters >= self.budget.queue_capacity:
                self._total_rejected += 1
                self._record_rejection("queue_capacity_exceeded")
                raise ConcurrencyLimitExceededError(
                    f"{self.component.capitalize()} overloaded: maximum concurrency limit of "
                    f"{self.budget.max_concurrent} reached and queue is full.",
                    component=self.component,
                    reason="queue_full",
                    current_in_flight=self._in_flight,
                    max_allowed=self.budget.max_concurrent,
                )

            self._queue_waiters += 1

        # Bounded queue wait outside lock
        wait_start = time.perf_counter()
        acquired = self._semaphore.acquire(timeout=eff_timeout)
        wait_duration = time.perf_counter() - wait_start

        with self._lock:
            self._queue_waiters -= 1

            if not acquired:
                self._total_timeouts += 1
                self._total_rejected += 1
                self._record_rejection("queue_timeout")
                raise ConcurrencyLimitExceededError(
                    f"{self.component.capitalize()} request timed out after waiting "
                    f"{wait_duration:.3f}s (budget limit {eff_timeout}s).",
                    component=self.component,
                    reason="queue_timeout",
                    current_in_flight=self._in_flight,
                    max_allowed=self.budget.max_concurrent,
                )

            self._in_flight += 1
            self._total_acquired += 1
            self._update_metrics()
            return _LimiterContext(self)

    def release(self) -> None:
        """Releases an acquired execution permit, signaling the semaphore."""
        with self._lock:
            if self._in_flight > 0:
                self._in_flight -= 1
                self._semaphore.release()
                self._update_metrics()

    def reset(self) -> None:
        """Resets the limiter state for isolated tests."""
        with self._lock:
            self._in_flight = 0
            self._queue_waiters = 0
            self._semaphore = threading.Semaphore(self.budget.max_concurrent)
            self._total_requests = 0
            self._total_acquired = 0
            self._total_rejected = 0
            self._total_timeouts = 0
            self._update_metrics()

    def get_stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "in_flight": self._in_flight,
                "queue_waiters": self._queue_waiters,
                "max_concurrent": self.budget.max_concurrent,
                "queue_capacity": self.budget.queue_capacity,
                "total_requests": self._total_requests,
                "total_acquired": self._total_acquired,
                "total_rejected": self._total_rejected,
                "total_timeouts": self._total_timeouts,
            }

    def _update_metrics(self) -> None:
        try:
            from infrastructure.monitoring.metrics import get_metrics_registry

            reg = get_metrics_registry()
            gauge_name = f"{self.component}_in_flight"
            reg.gauge(gauge_name).set(float(self._in_flight))
        except Exception:
            pass

    def _record_rejection(self, reason: str) -> None:
        try:
            from infrastructure.monitoring.metrics import get_metrics_registry

            reg = get_metrics_registry()
            reg.counter("concurrency_rejections_total").inc(
                1.0, labels={"component": self.component, "reason": reason}
            )
        except Exception:
            pass


class _LimiterContext:
    def __init__(self, limiter: ConcurrencyLimiter) -> None:
        self.limiter = limiter
        self._released = False

    def __enter__(self) -> _LimiterContext:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if not self._released:
            self._released = True
            self.limiter.release()


_DETECTOR_LIMITER: ConcurrencyLimiter | None = None
_JEV_LIMITER: ConcurrencyLimiter | None = None
_LIMITER_LOCK = threading.Lock()


def get_detector_limiter() -> ConcurrencyLimiter:
    global _DETECTOR_LIMITER
    with _LIMITER_LOCK:
        if _DETECTOR_LIMITER is None:
            from x_sentinel.config import settings

            _DETECTOR_LIMITER = ConcurrencyLimiter(
                "detector",
                ConcurrencyBudget(
                    max_concurrent=settings.max_concurrent_detector_requests,
                    queue_capacity=0,
                    queue_timeout_seconds=0.0,
                ),
            )
        return _DETECTOR_LIMITER


def get_jev_limiter() -> ConcurrencyLimiter:
    global _JEV_LIMITER
    with _LIMITER_LOCK:
        if _JEV_LIMITER is None:
            from x_sentinel.config import settings

            _JEV_LIMITER = ConcurrencyLimiter(
                "jev_ai",
                ConcurrencyBudget(
                    max_concurrent=settings.max_concurrent_ai_requests,
                    queue_capacity=settings.ai_queue_capacity,
                    queue_timeout_seconds=settings.ai_queue_timeout_seconds,
                ),
            )
        return _JEV_LIMITER


def reset_all_limiters() -> None:
    with _LIMITER_LOCK:
        if _DETECTOR_LIMITER is not None:
            _DETECTOR_LIMITER.reset()
        if _JEV_LIMITER is not None:
            _JEV_LIMITER.reset()
