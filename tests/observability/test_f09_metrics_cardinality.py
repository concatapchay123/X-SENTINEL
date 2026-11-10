"""Regression tests for Batch E: F09 (Metrics Cardinality Bound), F18 (View Map Caching)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from x_sentinel.data.views import load_view_map
from x_sentinel.main import app

from infrastructure.monitoring.metrics import (
    MAX_METRIC_SERIES_LIMIT,
    Counter,
    Histogram,
    get_metrics_registry,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_f09_unmatched_urls_bound_to_unmatched_endpoint():
    """F09: Arbitrary unknown/404 URLs must record under endpoint='unmatched' to prevent cardinality explosion."""
    client = TestClient(app)
    reg = get_metrics_registry()

    # Issue 25 distinct nonexistent endpoints
    for i in range(25):
        resp = client.get(f"/v1/random-unmatched-path-{i}/sub-{i}")
        assert resp.status_code in (404, 405)

    counter = reg.counter("api_requests_total")
    # Verify that no custom random URL became an endpoint label
    with counter._lock:
        endpoint_labels = {dict(k).get("endpoint") for k in counter._values.keys()}

    for i in range(25):
        assert f"/v1/random-unmatched-path-{i}/sub-{i}" not in endpoint_labels

    assert "unmatched" in endpoint_labels


def test_f09_metrics_max_series_limit_enforced():
    """F09: Counter and Histogram strictly clamp total series to MAX_METRIC_SERIES_LIMIT."""
    counter = Counter("test_cardinality_counter")
    for i in range(MAX_METRIC_SERIES_LIMIT + 50):
        counter.inc(1.0, labels={"endpoint": f"/test/path/{i}", "status_code": "200"})

    with counter._lock:
        assert len(counter._values) <= MAX_METRIC_SERIES_LIMIT + 1

    histogram = Histogram("test_cardinality_histogram")
    for i in range(MAX_METRIC_SERIES_LIMIT + 50):
        histogram.observe(10.0, labels={"endpoint": f"/test/path/{i}", "status_code": "200"})

    with histogram._lock:
        assert len(histogram._series) <= MAX_METRIC_SERIES_LIMIT + 1


def test_f18_view_map_caching():
    """F18: load_view_map uses LRU cache to avoid repeated disk reads."""
    view_path = PROJECT_ROOT / "configs" / "views.demo.yaml"
    vm1 = load_view_map(view_path, allow_demo=True)
    vm2 = load_view_map(view_path, allow_demo=True)

    # Identical object from LRU cache
    assert vm1 is vm2
