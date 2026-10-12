from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from x_sentinel.config import settings
from x_sentinel.database.base import Base
from x_sentinel.database.session import get_db
from x_sentinel.main import app

client = TestClient(app)


@pytest.fixture
def auth_test_db() -> Session:
    """Isolated in-memory database session fixture compatible with multi-threaded TestClient."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for col in Base.metadata.tables["audit_events"].columns:
        if col.name == "id":
            from sqlalchemy import Integer
            col.type = Integer()
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if col.server_default is not None:
                text_str = str(col.server_default.arg)
                if "N'" in text_str:
                    col.server_default.arg.text = text_str.replace("N'", "'")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_auth_disabled_mode_allows_unauthenticated_access(auth_test_db: Session) -> None:
    """When api_auth_mode == 'none', endpoints allow access without Authorization header."""
    def override_db():
        yield auth_test_db

    app.dependency_overrides[get_db] = override_db
    try:
        with patch.object(settings, "api_auth_mode", "none"):
            # GET /v1/analysis without headers returns 200
            resp_hist = client.get("/v1/analysis")
            assert resp_hist.status_code == 200
            assert resp_hist.json()["total"] == 0

            # GET /v1/alerts without headers returns 200
            resp_alerts = client.get("/v1/alerts")
            assert resp_alerts.status_code == 200
            assert resp_alerts.json()["total"] == 0

            # POST /v1/analyze/vector with valid dummy vector returns 200
            resp_analyze = client.post(
                "/v1/analyze/vector",
                json={"features": [0.0] * 2381, "request_id": f"req-auth-none-{uuid.uuid4()}"},
            )
            assert resp_analyze.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_auth_enabled_missing_credentials_rejected() -> None:
    """When api_auth_mode == 'bearer', requests missing Authorization header are rejected."""
    with patch.object(settings, "api_auth_mode", "bearer"):
        # /v1/analysis
        resp1 = client.get("/v1/analysis")
        assert resp1.status_code == 401
        assert resp1.json()["detail"]["code"] == "XS_UNAUTHENTICATED"

        # /v1/alerts
        resp2 = client.get("/v1/alerts")
        assert resp2.status_code == 401
        assert resp2.json()["detail"]["code"] == "XS_UNAUTHENTICATED"

        # /v1/analyze/vector
        resp3 = client.post(
            "/v1/analyze/vector",
            json={"features": [0.0] * 2381, "request_id": "test-req-001"},
        )
        assert resp3.status_code == 401
        assert resp3.json()["detail"]["code"] == "XS_UNAUTHENTICATED"

        # /v1/analysis/{id}/evidence
        resp4 = client.get("/v1/analysis/dummy-id/evidence")
        assert resp4.status_code == 401
        assert resp4.json()["detail"]["code"] == "XS_UNAUTHENTICATED"

        # PATCH /v1/alerts/{id}
        resp5 = client.patch("/v1/alerts/dummy-id", json={"status": "acknowledged"})
        assert resp5.status_code == 401
        assert resp5.json()["detail"]["code"] == "XS_UNAUTHENTICATED"


def test_auth_enabled_invalid_credentials_rejected() -> None:
    """When api_auth_mode == 'bearer', forged tokens return 401 XS_INVALID_CREDENTIALS."""
    with patch.object(settings, "api_auth_mode", "bearer"):
        forged_headers = {"Authorization": "Bearer forged-fake-token-xyz"}
        resp = client.get("/v1/analysis", headers=forged_headers)
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "XS_INVALID_CREDENTIALS"


def test_auth_enabled_role_enforcement_operator_forbidden_actions(auth_test_db: Session) -> None:
    """Operator cannot access evidence (requires admin/analyst/evaluator) or mutate alert status."""
    def override_db():
        yield auth_test_db

    app.dependency_overrides[get_db] = override_db
    try:
        with patch.object(settings, "api_auth_mode", "bearer"):
            operator_headers = {"Authorization": "Bearer token-operator"}

            # Operator reading evidence -> 403 Forbidden
            resp_ev = client.get("/v1/analysis/some-job-id/evidence", headers=operator_headers)
            assert resp_ev.status_code == 403
            assert resp_ev.json()["detail"]["code"] == "XS_FORBIDDEN"

            # Operator patching alert status -> 403 Forbidden
            resp_patch = client.patch(
                "/v1/alerts/some-alert-id",
                json={"status": "resolved"},
                headers=operator_headers,
            )
            assert resp_patch.status_code == 403
            assert resp_patch.json()["detail"]["code"] == "XS_FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


def test_auth_enabled_role_enforcement_evaluator_forbidden_actions(auth_test_db: Session) -> None:
    """Evaluator cannot submit vector analysis (requires admin/analyst/operator)."""
    def override_db():
        yield auth_test_db

    app.dependency_overrides[get_db] = override_db
    try:
        with patch.object(settings, "api_auth_mode", "bearer"):
            evaluator_headers = {"Authorization": "Bearer token-evaluator"}

            # Evaluator submitting analysis -> 403 Forbidden
            resp_post = client.post(
                "/v1/analyze/vector",
                json={"features": [0.0] * 2381, "request_id": "test-eval-forbidden"},
                headers=evaluator_headers,
            )
            assert resp_post.status_code == 403
            assert resp_post.json()["detail"]["code"] == "XS_FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


def test_auth_enabled_role_enforcement_analyst_permitted_actions(auth_test_db: Session) -> None:
    """Analyst has permissions to submit analysis, view history, view alerts, and view evidence."""
    def override_db():
        yield auth_test_db

    app.dependency_overrides[get_db] = override_db
    try:
        with patch.object(settings, "api_auth_mode", "bearer"):
            analyst_headers = {"Authorization": "Bearer token-analyst"}

            # 1. Analyst submitting vector
            req_id = f"req-analyst-{uuid.uuid4()}"
            resp_analyze = client.post(
                "/v1/analyze/vector",
                json={"features": [0.0] * 2381, "request_id": req_id},
                headers=analyst_headers,
            )
            assert resp_analyze.status_code == 200

            # 2. Analyst listing history
            resp_hist = client.get("/v1/analysis", headers=analyst_headers)
            assert resp_hist.status_code == 200

            # 3. Analyst listing alerts
            resp_alerts = client.get("/v1/alerts", headers=analyst_headers)
            assert resp_alerts.status_code == 200

            # 4. Analyst reading evidence for created job
            resp_ev = client.get(f"/v1/analysis/{req_id}/evidence", headers=analyst_headers)
            assert resp_ev.status_code == 200
            assert resp_ev.json()["verified"] is True
    finally:
        app.dependency_overrides.clear()


def test_auth_enabled_client_cannot_forge_roles_via_custom_headers(auth_test_db: Session) -> None:
    """Client cannot bypass role checks by injecting headers like X-Role or X-User-Role."""
    def override_db():
        yield auth_test_db

    app.dependency_overrides[get_db] = override_db
    try:
        with patch.object(settings, "api_auth_mode", "bearer"):
            forged_role_headers = {
                "Authorization": "Bearer token-operator",
                "X-Role": "admin",
                "X-User-Role": "admin",
                "Role": "admin",
            }

            resp = client.patch(
                "/v1/alerts/some-alert-id",
                json={"status": "resolved"},
                headers=forged_role_headers,
            )
            assert resp.status_code == 403
            assert resp.json()["detail"]["code"] == "XS_FORBIDDEN"
    finally:
        app.dependency_overrides.clear()
