from __future__ import annotations

import logging
import math
import threading
from collections.abc import Sequence
from enum import StrEnum
from typing import Any

logger = logging.getLogger("x_sentinel.monitoring.metrics")

# Forbidden high-cardinality label names to prevent unbounded memory growth
FORBIDDEN_LABEL_KEYS = frozenset(
    {
        "request_id",
        "analysis_id",
        "job_id",
        "run_id",
        "user_id",
        "input_id",
        "hash",
        "evidence_hash",
        "input_hash",
        "digest",
        "prompt",
        "token",
        "payload",
        "vector",
        "secret",
        "authorization",
    }
)


class MetricType(StrEnum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class HighCardinalityLabelError(ValueError):
    """Raised when a forbidden high-cardinality label is passed into metric observation."""


def _format_labels(labels: dict[str, str] | None) -> str:
    if not labels:
        return ""
    sorted_items = sorted(labels.items())
    parts = [f'{k}="{v}"' for k, v in sorted_items]
    return "{" + ",".join(parts) + "}"


def _validate_label_dict(labels: dict[str, str] | None) -> dict[str, str]:
    if not labels:
        return {}
    cleaned: dict[str, str] = {}
    for k, v in labels.items():
        lk = str(k).strip().lower()
        if lk in FORBIDDEN_LABEL_KEYS:
            raise HighCardinalityLabelError(
                f"Forbidden high-cardinality metric label key: '{k}'."
            )
        cleaned[str(k).strip()] = str(v).strip()
    return cleaned


class Counter:
    """Thread-safe cumulative counter metric."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self.metric_type = MetricType.COUNTER
        self._lock = threading.Lock()
        self._values: dict[frozenset[tuple[str, str]], float] = {}

    def inc(self, amount: float = 1.0, labels: dict[str, str] | None = None) -> None:
        if amount < 0:
            raise ValueError(f"Counter increments must be non-negative; got {amount}")
        clean_lbl = _validate_label_dict(labels)
        key = frozenset(clean_lbl.items())
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def get(self, labels: dict[str, str] | None = None) -> float:
        clean_lbl = _validate_label_dict(labels)
        key = frozenset(clean_lbl.items())
        with self._lock:
            return self._values.get(key, 0.0)

    def reset(self) -> None:
        with self._lock:
            self._values.clear()

    def to_prometheus_lines(self) -> list[str]:
        lines: list[str] = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter",
        ]
        with self._lock:
            if not self._values:
                lines.append(f"{self.name} 0.0")
            else:
                for key, val in sorted(self._values.items(), key=lambda x: sorted(list(x[0]))):
                    lbl_str = _format_labels(dict(key))
                    lines.append(f"{self.name}{lbl_str} {val}")
        return lines


class Gauge:
    """Thread-safe gauge representing an arbitrary variable numeric state."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self.metric_type = MetricType.GAUGE
        self._lock = threading.Lock()
        self._values: dict[frozenset[tuple[str, str]], float] = {}

    def set(self, val: float, labels: dict[str, str] | None = None) -> None:
        if not math.isfinite(val):
            raise ValueError(f"Gauge value must be finite; got {val}")
        clean_lbl = _validate_label_dict(labels)
        key = frozenset(clean_lbl.items())
        with self._lock:
            self._values[key] = float(val)

    def inc(self, amount: float = 1.0, labels: dict[str, str] | None = None) -> None:
        clean_lbl = _validate_label_dict(labels)
        key = frozenset(clean_lbl.items())
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def dec(self, amount: float = 1.0, labels: dict[str, str] | None = None) -> None:
        clean_lbl = _validate_label_dict(labels)
        key = frozenset(clean_lbl.items())
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) - amount

    def get(self, labels: dict[str, str] | None = None) -> float:
        clean_lbl = _validate_label_dict(labels)
        key = frozenset(clean_lbl.items())
        with self._lock:
            return self._values.get(key, 0.0)

    def reset(self) -> None:
        with self._lock:
            self._values.clear()

    def to_prometheus_lines(self) -> list[str]:
        lines: list[str] = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge",
        ]
        with self._lock:
            if not self._values:
                lines.append(f"{self.name} 0.0")
            else:
                for key, val in sorted(self._values.items(), key=lambda x: sorted(list(x[0]))):
                    lbl_str = _format_labels(dict(key))
                    lines.append(f"{self.name}{lbl_str} {val}")
        return lines


class Histogram:
    """Thread-safe histogram tracking duration distributions across cumulative buckets."""

    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: Sequence[float] = (
            1.0,
            2.5,
            5.0,
            8.0,
            10.0,
            15.0,
            25.0,
            50.0,
            100.0,
            250.0,
            500.0,
            1000.0,
        ),
    ) -> None:
        self.name = name
        self.description = description
        self.metric_type = MetricType.HISTOGRAM
        self.buckets = sorted(float(b) for b in buckets)
        self._lock = threading.Lock()
        # Storage: key -> {"count": int, "sum": float, "buckets": {bucket_le: int}}
        self._series: dict[frozenset[tuple[str, str]], dict[str, Any]] = {}

    def observe(self, val: float, labels: dict[str, str] | None = None) -> None:
        if not math.isfinite(val) or val < 0.0:
            raise ValueError(f"Histogram observation must be non-negative finite float; got {val}")
        clean_lbl = _validate_label_dict(labels)
        key = frozenset(clean_lbl.items())

        with self._lock:
            if key not in self._series:
                b_map = {b: 0 for b in self.buckets}
                b_map[float("inf")] = 0
                self._series[key] = {"count": 0, "sum": 0.0, "buckets": b_map}

            rec = self._series[key]
            rec["count"] += 1
            rec["sum"] += float(val)

            # Update cumulative bucket counts
            for b in self.buckets:
                if val <= b:
                    rec["buckets"][b] += 1
            rec["buckets"][float("inf")] += 1

    def get_summary(self, labels: dict[str, str] | None = None) -> dict[str, Any]:
        clean_lbl = _validate_label_dict(labels)
        key = frozenset(clean_lbl.items())
        with self._lock:
            rec = self._series.get(key)
            if rec is None:
                return {"count": 0, "sum": 0.0, "buckets": {b: 0 for b in self.buckets}}
            return {
                "count": rec["count"],
                "sum": round(rec["sum"], 4),
                "buckets": dict(rec["buckets"]),
            }

    def reset(self) -> None:
        with self._lock:
            self._series.clear()

    def to_prometheus_lines(self) -> list[str]:
        lines: list[str] = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]
        with self._lock:
            if not self._series:
                for b in self.buckets:
                    lines.append(f'{self.name}_bucket{{le="{b}"}} 0')
                lines.append(f'{self.name}_bucket{{le="+Inf"}} 0')
                lines.append(f"{self.name}_count 0")
                lines.append(f"{self.name}_sum 0.0")
            else:
                for key, rec in sorted(self._series.items(), key=lambda x: sorted(list(x[0]))):
                    base_labels = dict(key)
                    for b in self.buckets:
                        lbls = dict(base_labels)
                        lbls["le"] = str(b)
                        lines.append(f"{self.name}_bucket{_format_labels(lbls)} {rec['buckets'][b]}")
                    inf_lbls = dict(base_labels)
                    inf_lbls["le"] = "+Inf"
                    lines.append(
                        f"{self.name}_bucket{_format_labels(inf_lbls)} {rec['buckets'][float('inf')]}"
                    )
                    lines.append(f"{self.name}_count{_format_labels(base_labels)} {rec['count']}")
                    lines.append(f"{self.name}_sum{_format_labels(base_labels)} {rec['sum']}")
        return lines


class MetricsRegistry:
    """Thread-safe registry for managing all application observability metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}

    def counter(self, name: str, description: str = "") -> Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, description)
            return self._counters[name]

    def gauge(self, name: str, description: str = "") -> Gauge:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, description)
            return self._gauges[name]

    def histogram(
        self,
        name: str,
        description: str = "",
        buckets: Sequence[float] = (
            1.0,
            2.5,
            5.0,
            8.0,
            10.0,
            15.0,
            25.0,
            50.0,
            100.0,
            250.0,
            500.0,
            1000.0,
        ),
    ) -> Histogram:
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, description, buckets=buckets)
            return self._histograms[name]

    def generate_prometheus_text(self) -> str:
        lines: list[str] = []
        with self._lock:
            for c in sorted(self._counters.values(), key=lambda m: m.name):
                lines.extend(c.to_prometheus_lines())
            for g in sorted(self._gauges.values(), key=lambda m: m.name):
                lines.extend(g.to_prometheus_lines())
            for h in sorted(self._histograms.values(), key=lambda m: m.name):
                lines.extend(h.to_prometheus_lines())
        return "\n".join(lines) + "\n"

    def reset_all(self) -> None:
        with self._lock:
            for c in self._counters.values():
                c.reset()
            for g in self._gauges.values():
                g.reset()
            for h in self._histograms.values():
                h.reset()


_GLOBAL_REGISTRY: MetricsRegistry | None = None
_GLOBAL_REGISTRY_LOCK = threading.Lock()


def get_metrics_registry() -> MetricsRegistry:
    """Returns the process-wide metrics registry, initializing canonical metrics on first call."""
    global _GLOBAL_REGISTRY
    with _GLOBAL_REGISTRY_LOCK:
        if _GLOBAL_REGISTRY is None:
            reg = MetricsRegistry()
            # 1. Detector metrics
            reg.histogram(
                "detector_latency_ms",
                "Total end-to-end detector latency in milliseconds",
                buckets=[1.0, 2.5, 5.0, 8.0, 10.0, 15.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0],
            )
            reg.histogram(
                "detector_stage_latency_ms",
                "Sub-stage detector latency in milliseconds (model, shap, signals, fusion, input_validation, persistence)",
                buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0, 20.0, 50.0, 100.0, 250.0],
            )
            reg.counter(
                "detector_requests_total",
                "Total number of detector analysis requests completed",
            )
            reg.gauge(
                "detector_in_flight",
                "Current number of in-flight detector requests being evaluated",
            )

            # 2. Jev AI metrics
            reg.histogram(
                "jev_latency_ms",
                "Total end-to-end Jev AI advisory workflow latency in milliseconds",
                buckets=[25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0, 10000.0, 30000.0, 60000.0],
            )
            reg.histogram(
                "jev_stage_latency_ms",
                "Jev AI sub-stage latency in milliseconds (context_building, runtime_http, response_validation, persistence)",
                buckets=[5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 5000.0, 10000.0],
            )
            reg.counter(
                "jev_requests_total",
                "Total number of Jev AI advisory runs completed or failed",
            )
            reg.gauge(
                "jev_in_flight",
                "Current number of in-flight Jev AI requests being processed",
            )

            # 3. Platform & API metrics
            reg.histogram(
                "api_request_latency_ms",
                "HTTP request duration in milliseconds measured at API edge",
                buckets=[1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0],
            )
            reg.counter(
                "api_requests_total",
                "Total number of HTTP API requests serviced",
            )
            reg.counter(
                "concurrency_rejections_total",
                "Total number of requests rejected due to concurrency or queue budget exhaustion",
            )

            # 4. System telemetry gauges
            reg.gauge("system_cpu_percent", "Current host CPU utilization percentage")
            reg.gauge("system_ram_used_bytes", "Current host RAM memory used in bytes")
            reg.gauge("system_ram_percent", "Current host RAM memory used percentage")
            reg.gauge("system_thread_count", "Current process active thread count")

            _GLOBAL_REGISTRY = reg
        return _GLOBAL_REGISTRY


def safe_record_metric(metric_fn: Any, *args: Any, **kwargs: Any) -> None:
    """Invokes a metric recording function fail-safe without ever interrupting caller logic."""
    try:
        metric_fn(*args, **kwargs)
    except Exception as exc:
        logger.warning("Observability fail-safe caught metric recording error: %s", exc)
