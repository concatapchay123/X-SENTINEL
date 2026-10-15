from __future__ import annotations

import concurrent.futures
import threading
import time

import pytest

from infrastructure.monitoring.concurrency import (
    ConcurrencyBudget,
    ConcurrencyLimiter,
    ConcurrencyLimitExceededError,
)


class TestConcurrencyLimiter:
    def test_single_acquire_release_lifecycle(self) -> None:
        limiter = ConcurrencyLimiter(
            "test_comp",
            ConcurrencyBudget(max_concurrent=5, queue_capacity=10),
        )
        assert limiter.in_flight == 0

        with limiter.acquire():
            assert limiter.in_flight == 1

        assert limiter.in_flight == 0

    def test_concurrency_limit_exhaustion_immediate_rejection(self) -> None:
        limiter = ConcurrencyLimiter(
            "detector",
            ConcurrencyBudget(max_concurrent=2, queue_capacity=0, queue_timeout_seconds=0.0),
        )

        ctx1 = limiter.acquire()
        ctx2 = limiter.acquire()
        assert limiter.in_flight == 2

        with pytest.raises(ConcurrencyLimitExceededError) as exc_info:
            limiter.acquire()

        assert exc_info.value.component == "detector"
        assert exc_info.value.reason == "queue_full"
        assert exc_info.value.current_in_flight == 2
        assert exc_info.value.max_allowed == 2

        # Release permits
        ctx1.__exit__(None, None, None)
        ctx2.__exit__(None, None, None)
        assert limiter.in_flight == 0

    def test_queue_wait_and_success_handoff(self) -> None:
        limiter = ConcurrencyLimiter(
            "jev_ai",
            ConcurrencyBudget(max_concurrent=1, queue_capacity=5, queue_timeout_seconds=2.0),
        )

        order: list[str] = []
        w1_started = threading.Event()

        def worker1() -> None:
            with limiter.acquire():
                order.append("w1_acquired")
                w1_started.set()
                time.sleep(0.05)
                order.append("w1_releasing")

        def worker2() -> None:
            assert w1_started.wait(timeout=2.0), "worker1 failed to start"
            time.sleep(0.005)  # ensure w1 is firmly holding permit and worker1 is inside block
            with limiter.acquire():
                order.append("w2_acquired")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(worker1)
            f2 = executor.submit(worker2)
            f1.result()
            f2.result()

        assert order == ["w1_acquired", "w1_releasing", "w2_acquired"]
        assert limiter.in_flight == 0

    def test_queue_timeout_rejection(self) -> None:
        limiter = ConcurrencyLimiter(
            "jev_ai",
            ConcurrencyBudget(max_concurrent=1, queue_capacity=2, queue_timeout_seconds=0.05),
        )

        ctx1 = limiter.acquire()
        assert limiter.in_flight == 1

        with pytest.raises(ConcurrencyLimitExceededError) as exc_info:
            limiter.acquire()

        assert exc_info.value.reason == "queue_timeout"
        ctx1.__exit__(None, None, None)
        assert limiter.in_flight == 0

    def test_exception_guarantees_permit_release(self) -> None:
        limiter = ConcurrencyLimiter(
            "robust_comp",
            ConcurrencyBudget(max_concurrent=1),
        )

        with pytest.raises(RuntimeError):
            with limiter.acquire():
                assert limiter.in_flight == 1
                raise RuntimeError("critical failure inside guarded section")

        assert limiter.in_flight == 0

    def test_multithreaded_high_contention_no_deadlock(self) -> None:
        limiter = ConcurrencyLimiter(
            "contention_test",
            ConcurrencyBudget(max_concurrent=3, queue_capacity=50, queue_timeout_seconds=5.0),
        )

        completed_tasks = 0
        total_tasks = 25

        def worker() -> None:
            nonlocal completed_tasks
            with limiter.acquire():
                time.sleep(0.005)
                completed_tasks += 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker) for _ in range(total_tasks)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        assert completed_tasks == total_tasks
        assert limiter.in_flight == 0

    def test_recovery_after_overload(self) -> None:
        limiter = ConcurrencyLimiter(
            "recovery_test",
            ConcurrencyBudget(max_concurrent=1, queue_capacity=0),
        )

        # Force overload
        ctx = limiter.acquire()
        with pytest.raises(ConcurrencyLimitExceededError):
            limiter.acquire()

        # Release and recover
        ctx.__exit__(None, None, None)
        assert limiter.in_flight == 0

        # Subsequent requests must succeed cleanly
        with limiter.acquire():
            assert limiter.in_flight == 1
        assert limiter.in_flight == 0

    def test_concurrent_burst_zero_queue_rejection_reasons_strictly_queue_full(self) -> None:
        """High concurrency burst into zero-queue limiter must only reject with queue_full (zero queue_timeouts)."""
        limiter = ConcurrencyLimiter(
            "burst_comp",
            ConcurrencyBudget(max_concurrent=2, queue_capacity=0, queue_timeout_seconds=0.0),
        )
        rejection_reasons: list[str] = []
        admitted = 0

        def worker() -> None:
            nonlocal admitted
            try:
                with limiter.acquire():
                    admitted += 1
                    time.sleep(0.02)
            except ConcurrencyLimitExceededError as exc:
                rejection_reasons.append(exc.reason)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(10)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        stats = limiter.get_stats()
        assert stats["total_timeouts"] == 0, "Zero-queue limiter must never record timeouts"
        assert all(r == "queue_full" for r in rejection_reasons)
        assert admitted <= 2
        assert len(rejection_reasons) >= 8
        assert limiter.in_flight == 0
