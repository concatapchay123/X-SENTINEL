from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from x_sentinel.main import app
from x_sentinel.security.auth import Role

from infrastructure.monitoring.metrics import (
    Counter,
    Gauge,
    HighCardinalityLabelError,
    Histogram,
    MetricsRegistry,
    safe_record_metric,
)
from infrastructure.monitoring.telemetry import collect_system_telemetry

client = TestClient(app)


def _auth_header_for_roles(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer token-{role}"}


class TestMetricsPrimitives:
    def test_counter_increments_and_resets(self) -> None:
        c = Counter("test_counter", "sample counter")
        assert c.get() == 0.0

        c.inc(1.0)
        c.inc(2.5)
        assert c.get() == 3.5

        c.inc(1.0, labels={"status": "ok"})
        assert c.get(labels={"status": "ok"}) == 1.0
        assert c.get() == 3.5

        with pytest.raises(ValueError, match="non-negative"):
            c.inc(-1.0)

        c.reset()
        assert c.get() == 0.0

    def test_gauge_set_inc_dec(self) -> None:
        g = Gauge("test_gauge", "sample gauge")
        g.set(10.0)
        assert g.get() == 10.0

        g.inc(2.0)
        assert g.get() == 12.0

        g.dec(5.0)
        assert g.get() == 7.0

        g.reset()
        assert g.get() == 0.0

    def test_histogram_bucket_distribution(self) -> None:
        h = Histogram("test_hist", "sample hist", buckets=[5.0, 10.0, 20.0])
        h.observe(3.0)
        h.observe(7.0)
        h.observe(15.0)
        h.observe(25.0)

        summary = h.get_summary()
        assert summary["count"] == 4
        assert summary["sum"] == 50.0

        # Cumulative bucket counts:
        # <= 5.0: 1 (3.0)
        # <= 10.0: 2 (3.0, 7.0)
        # <= 20.0: 3 (3.0, 7.0, 15.0)
        # <= inf: 4
        buckets = summary["buckets"]
        assert buckets[5.0] == 1
        assert buckets[10.0] == 2
        assert buckets[20.0] == 3
        assert buckets[float("inf")] == 4

    def test_forbidden_high_cardinality_labels_rejected(self) -> None:
        c = Counter("safe_counter")
        with pytest.raises(HighCardinalityLabelError, match="Forbidden high-cardinality"):
            c.inc(1.0, labels={"request_id": "req-12345"})

        with pytest.raises(HighCardinalityLabelError, match="Forbidden high-cardinality"):
            c.inc(1.0, labels={"token": "tok-abcde"})

        with pytest.raises(HighCardinalityLabelError, match="Forbidden high-cardinality"):
            c.inc(1.0, labels={"hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"})

    def test_prometheus_exposition_format(self) -> None:
        reg = MetricsRegistry()
        c = reg.counter("http_requests", "Total requests")
        c.inc(5.0, labels={"method": "GET"})
        g = reg.gauge("active_workers", "Active count")
        g.set(4.0)

        text = reg.generate_prometheus_text()
        assert "# HELP http_requests Total requests" in text
        assert "# TYPE http_requests counter" in text
        assert 'http_requests{method="GET"} 5.0' in text
        assert "# TYPE active_workers gauge" in text
        assert "active_workers 4.0" in text

    def test_fail_safe_metric_recording(self) -> None:
        def bad_metric():
            raise RuntimeError("Collector network failed")

        # Must not raise
        safe_record_metric(bad_metric)


class TestAuthenticTelemetry:
    def test_authentic_system_telemetry_returns_real_os_metrics(self) -> None:
        telemetry = collect_system_telemetry()
        assert telemetry["status"] == "ok"
        assert "cpu" in telemetry
        assert "memory" in telemetry
        assert "process" in telemetry

        # Verify authentic values
        assert telemetry["cpu"]["logical_cores"] > 0
        assert telemetry["memory"]["total_bytes"] > 1024 * 1024  # > 1MB
        assert telemetry["process"]["pid"] > 0
        assert telemetry["process"]["rss_bytes"] > 0
        assert telemetry["process"]["thread_count"] > 0


class TestObservabilityEndpoints:
    def test_metrics_endpoint_scrapes_successfully(self) -> None:
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        assert "detector_latency_ms" in resp.text
        assert "jev_latency_ms" in resp.text
        assert "api_request_latency_ms" in resp.text

    def test_system_metrics_endpoint_rbac(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from x_sentinel.config import settings

        monkeypatch.setattr(settings, "api_auth_mode", "predefined")
        # Admin permitted
        resp_admin = client.get(
            "/v1/system/metrics",
            headers=_auth_header_for_roles(Role.ADMIN.value),
        )
        assert resp_admin.status_code == 200
        assert "detector_latency_ms" in resp_admin.text

        # Operator permitted
        resp_op = client.get(
            "/v1/system/metrics",
            headers=_auth_header_for_roles(Role.OPERATOR.value),
        )
        assert resp_op.status_code == 200

    def test_system_telemetry_endpoint(self) -> None:
        resp = client.get(
            "/v1/system/telemetry",
            headers=_auth_header_for_roles(Role.ADMIN.value),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "cpu" in data
        assert "memory" in data

    def test_system_endpoints_reject_unauthorized_roles(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Evaluator role and unauthenticated requests must be strictly rejected from system telemetry and metrics."""
        from x_sentinel.config import settings

        monkeypatch.setattr(settings, "api_auth_mode", "predefined")
        # Evaluator lacks admin/operator role -> 403 Forbidden
        hdr = _auth_header_for_roles(Role.EVALUATOR.value)
        resp_m = client.get("/v1/system/metrics", headers=hdr)
        assert resp_m.status_code == 403, f"Expected 403 for evaluator on /v1/system/metrics, got {resp_m.status_code}"

        resp_t = client.get("/v1/system/telemetry", headers=hdr)
        assert resp_t.status_code == 403, f"Expected 403 for evaluator on /v1/system/telemetry, got {resp_t.status_code}"

        # Unauthenticated request -> 401
        resp_unauth_m = client.get("/v1/system/metrics")
        assert resp_unauth_m.status_code == 401

        resp_unauth_t = client.get("/v1/system/telemetry")
        assert resp_unauth_t.status_code == 401

    def test_metrics_disabled_returns_404(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from x_sentinel.config import settings

        monkeypatch.setattr(settings, "metrics_export_enabled", False)
        resp = client.get("/metrics")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "XS_FEATURE_DISABLED"

        resp_sys = client.get(
            "/v1/system/metrics",
            headers=_auth_header_for_roles(Role.ADMIN.value),
        )
        assert resp_sys.status_code == 404
        assert resp_sys.json()["detail"]["code"] == "XS_FEATURE_DISABLED"
