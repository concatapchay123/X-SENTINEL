from __future__ import annotations

from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from x_sentinel.config import settings
from x_sentinel.database.health import (
    DatabaseHealth,
    classify_revision_status,
    database_health,
)
from x_sentinel.jev_ai.schemas import JevStatus
from x_sentinel.jev_ai.status import get_jev_status
from x_sentinel.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test Suite 1: Health Endpoint (Liveness)
# ---------------------------------------------------------------------------


def test_health_endpoint_liveness_success() -> None:
    """GET /health must respond 200 with service liveness metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "x-sentinel"
    assert data["version"] == "v3"
    assert "demo_mode" in data
    assert "jev_ai_enabled" in data


def test_health_independent_of_database() -> None:
    """Liveness must not fail even if database connectivity fails."""
    with patch("x_sentinel.main.database_health") as mock_db_health:
        mock_db_health.return_value = DatabaseHealth(
            ok=False,
            reachable=False,
            current_revision=None,
            expected_revision=settings.expected_db_revision,
            status="unavailable",
            revision_status="unknown",
            error="OperationalError: database connection failed",
        )
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_health_independent_of_jev_ai() -> None:
    """Liveness must not fail even if Jev AI is enabled and LM Studio is unavailable."""
    with patch.object(settings, "jev_ai_enabled", True):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["jev_ai_enabled"] is True


# ---------------------------------------------------------------------------
# Test Suite 2: Database Revision Readiness
# ---------------------------------------------------------------------------


def test_classify_revision_status_logic() -> None:
    """Test Alembic revision classification for all supported states."""
    expected = "0002_v3_jev_ai_audit"

    # Current: exactly matches expected
    assert classify_revision_status("0002_v3_jev_ai_audit", expected) == "current"

    # Behind: ancestor in Alembic chain
    assert classify_revision_status("0001_v2_multiuser", expected) == "behind"

    # Unmigrated: None or empty string
    assert classify_revision_status(None, expected) == "unmigrated"
    assert classify_revision_status("", expected) == "unmigrated"

    # Unknown: revision not found in Alembic history
    assert classify_revision_status("nonexistent_rev_xyz", expected) == "unknown"


def test_database_health_current_revision() -> None:
    """When DB has alembic_version == expected_db_revision, database is ready."""
    eng = create_engine("sqlite:///:memory:")
    with eng.connect() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:rev)"),
            {"rev": settings.expected_db_revision},
        )
        conn.commit()

    health = database_health(engine_override=eng)
    assert health.ok is True
    assert health.reachable is True
    assert health.status == "ready"
    assert health.revision_status == "current"
    assert health.current_revision == settings.expected_db_revision
    assert health.expected_revision == settings.expected_db_revision
    assert health.error is None
    eng.dispose()


def test_database_health_behind_revision() -> None:
    """When DB has an older migration revision, report behind and not ready."""
    eng = create_engine("sqlite:///:memory:")
    with eng.connect() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('0001_v2_multiuser')"),
        )
        conn.commit()

    health = database_health(engine_override=eng)
    assert health.ok is False
    assert health.reachable is True
    assert health.status == "not_ready"
    assert health.revision_status == "behind"
    assert health.current_revision == "0001_v2_multiuser"
    assert health.error is not None
    assert "behind expected head" in health.error
    eng.dispose()


def test_database_health_unmigrated_missing_table() -> None:
    """When DB is reachable but alembic_version table is missing, report unmigrated."""
    eng = create_engine("sqlite:///:memory:")
    health = database_health(engine_override=eng)
    assert health.ok is False
    assert health.reachable is True
    assert health.status == "not_ready"
    assert health.revision_status == "unmigrated"
    assert health.current_revision is None
    assert health.error is not None
    assert "absent or unmigrated" in health.error
    eng.dispose()


def test_database_health_unmigrated_empty_table() -> None:
    """When alembic_version exists but contains no rows, report unmigrated."""
    eng = create_engine("sqlite:///:memory:")
    with eng.connect() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.commit()

    health = database_health(engine_override=eng)
    assert health.ok is False
    assert health.reachable is True
    assert health.status == "not_ready"
    assert health.revision_status == "unmigrated"
    assert health.current_revision is None
    eng.dispose()


def test_database_health_unknown_revision() -> None:
    """When DB contains an alien/unknown revision, report unknown mismatch."""
    eng = create_engine("sqlite:///:memory:")
    with eng.connect() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('corrupted_rev_999')"),
        )
        conn.commit()

    health = database_health(engine_override=eng)
    assert health.ok is False
    assert health.reachable is True
    assert health.status == "not_ready"
    assert health.revision_status == "unknown"
    assert health.current_revision == "corrupted_rev_999"
    eng.dispose()


def test_database_health_unreachable() -> None:
    """When DB connection fails, report unreachable without crashing."""
    broken_engine = create_engine("sqlite:///non_existent_folder_abc/unreachable.db")
    health = database_health(engine_override=broken_engine)
    assert health.ok is False
    assert health.reachable is False
    assert health.status == "unavailable"
    assert health.revision_status == "unknown"
    assert health.error is not None
    assert "database connection failed" in health.error


def test_ready_endpoint_db_ready() -> None:
    """Case A: App alive, DB ready, Jev disabled -> ready=PASS (200 OK)."""
    with patch("x_sentinel.main.database_health") as mock_db:
        mock_db.return_value = DatabaseHealth(
            ok=True,
            reachable=True,
            current_revision="0002_v3_jev_ai_audit",
            expected_revision="0002_v3_jev_ai_audit",
            status="ready",
            revision_status="current",
            error=None,
        )
        with patch.object(settings, "jev_ai_enabled", False):
            response = client.get("/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["database"]["ok"] is True
            assert data["database"]["revision_status"] == "current"
            assert data["jev_ai"]["enabled"] is False
            assert data["jev_ai"]["status"] == "disabled"
            assert data["jev_ai"]["readiness_blocking"] is False
            assert data["blockers"] == []


def test_ready_endpoint_db_unavailable() -> None:
    """Case C: App alive, DB unavailable -> ready=NOT_READY (503 Service Unavailable)."""
    with patch("x_sentinel.main.database_health") as mock_db:
        mock_db.return_value = DatabaseHealth(
            ok=False,
            reachable=False,
            current_revision=None,
            expected_revision="0002_v3_jev_ai_audit",
            status="unavailable",
            revision_status="unknown",
            error="OperationalError: database connection failed",
        )
        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["database"]["ok"] is False
        assert data["database"]["status"] == "unavailable"
        assert len(data["blockers"]) > 0


def test_ready_endpoint_db_revision_mismatch() -> None:
    """Case D: DB connected, migration revision mismatch -> ready=NOT_READY (503)."""
    with patch("x_sentinel.main.database_health") as mock_db:
        mock_db.return_value = DatabaseHealth(
            ok=False,
            reachable=True,
            current_revision="0001_v2_multiuser",
            expected_revision="0002_v3_jev_ai_audit",
            status="not_ready",
            revision_status="behind",
            error="database migration revision mismatch: database is behind expected head",
        )
        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["database"]["ok"] is False
        assert data["database"]["revision_status"] == "behind"
        assert len(data["blockers"]) > 0


def test_ready_endpoint_readiness_is_readonly() -> None:
    """Readiness inspection must never mutate database schema or execute migrations."""
    eng = create_engine("sqlite:///:memory:")
    with eng.connect() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('0001_v2_multiuser')"),
        )
        conn.commit()

    with patch("x_sentinel.main.database_health") as mock_health:
        mock_health.side_effect = lambda: database_health(engine_override=eng)
        resp = client.get("/ready")
        assert resp.status_code == 503

        # Confirm the database version was NOT modified
        with eng.connect() as conn:
            rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert rev == "0001_v2_multiuser"
    eng.dispose()


# ---------------------------------------------------------------------------
# Test Suite 3: Jev AI Disabled & Isolation State
# ---------------------------------------------------------------------------


def test_ai_disabled_zero_network_calls() -> None:
    """When XS_JEV_AI_ENABLED=false, get_jev_status must make zero HTTP calls."""
    with patch.object(settings, "jev_ai_enabled", False):
        mock_client = httpx.Client()
        with patch.object(mock_client, "get") as mock_get:
            status_res = get_jev_status(client=mock_client)
            assert mock_get.call_count == 0
            assert status_res.enabled is False
            assert status_res.status == JevStatus.DISABLED
            assert status_res.readiness_blocking is False
            assert status_res.model_id is None
            assert status_res.error is None


def test_ai_disabled_api_status_endpoint() -> None:
    """GET /v1/ai/status returns explicit disabled status without error."""
    with patch.object(settings, "jev_ai_enabled", False):
        response = client.get("/v1/ai/status")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["status"] == "disabled"
        assert data["advisory_only"] is True
        assert data["readiness_blocking"] is False
        assert data["endpoint_label"] == "lm_studio_local"


def test_ai_disabled_does_not_block_backend_readiness() -> None:
    """Jev AI disabled state must not block detector readiness."""
    with patch("x_sentinel.main.database_health") as mock_db:
        mock_db.return_value = DatabaseHealth(
            ok=True,
            reachable=True,
            current_revision="0002_v3_jev_ai_audit",
            expected_revision="0002_v3_jev_ai_audit",
            status="ready",
            revision_status="current",
            error=None,
        )
        with patch.object(settings, "jev_ai_enabled", False):
            response = client.get("/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["jev_ai"]["status"] == "disabled"
            assert data["jev_ai"]["readiness_blocking"] is False


# ---------------------------------------------------------------------------
# Test Suite 4: Jev AI Enabled & Unavailable State (Case B)
# ---------------------------------------------------------------------------


def test_ai_enabled_lm_studio_unavailable_does_not_block_readiness() -> None:
    """Case B: App alive, DB ready, Jev enabled, LM Studio down -> ready=PASS (200 OK)."""
    with patch("x_sentinel.main.database_health") as mock_db:
        mock_db.return_value = DatabaseHealth(
            ok=True,
            reachable=True,
            current_revision="0002_v3_jev_ai_audit",
            expected_revision="0002_v3_jev_ai_audit",
            status="ready",
            revision_status="current",
            error=None,
        )
        # Point to closed port
        with patch.object(settings, "jev_ai_enabled", True), \
             patch.object(settings, "jev_ai_base_url", "http://127.0.0.1:59999/v1"):
            # GET /v1/ai/status returns unavailable
            status_resp = client.get("/v1/ai/status")
            assert status_resp.status_code == 200
            assert status_resp.json()["status"] == "unavailable"
            assert status_resp.json()["readiness_blocking"] is False

            # GET /ready still returns 200 OK!
            ready_resp = client.get("/ready")
            assert ready_resp.status_code == 200
            ready_data = ready_resp.json()
            assert ready_data["status"] == "ready"
            assert ready_data["jev_ai"]["enabled"] is True
            assert ready_data["jev_ai"]["status"] == "unavailable"
            assert ready_data["jev_ai"]["readiness_blocking"] is False
            assert ready_data["blockers"] == []


def test_ai_enabled_lm_studio_available() -> None:
    """When LM Studio responds with 200, Jev status is available."""
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json={"data": [{"id": "jev-local-TBD"}]},
        )
    )
    mock_client = httpx.Client(transport=mock_transport)

    with patch.object(settings, "jev_ai_enabled", True):
        status = get_jev_status(client=mock_client)
        assert status.enabled is True
        assert status.status == JevStatus.AVAILABLE
        assert status.model_id == settings.jev_ai_model
        assert status.readiness_blocking is False
        assert status.error is None


def test_ai_enabled_misconfigured_endpoint() -> None:
    """When Jev base_url violates local_only allowlist, report misconfigured."""
    with patch.object(settings, "jev_ai_enabled", True), \
         patch.object(settings, "jev_ai_base_url", "https://api.openai.com/v1"), \
         patch.object(settings, "jev_ai_local_only", True):
        status = get_jev_status()
        assert status.enabled is True
        assert status.status == JevStatus.MISCONFIGURED
        assert status.readiness_blocking is False
        assert "XS_AI_CONTEXT_BLOCKED" in (status.error or "")


# ---------------------------------------------------------------------------
# Test Suite 5: Security & No Secret Leakage
# ---------------------------------------------------------------------------


def test_security_no_secrets_in_health_or_ready_responses() -> None:
    """Verify that neither /health, /ready, /v1/config/status nor /v1/ai/status leak credentials."""
    sensitive_patterns = [
        "password",
        "secret",
        "trusted_connection",
        "mssql+pyodbc",
        "driver=ODBC",
        "api_key",
        "token",
    ]

    for endpoint in ["/health", "/ready", "/v1/config/status", "/v1/ai/status"]:
        resp = client.get(endpoint)
        body = resp.text.lower()
        for pattern in sensitive_patterns:
            assert pattern not in body, f"Secret pattern '{pattern}' leaked in {endpoint}"


# ---------------------------------------------------------------------------
# Test Suite 6: Configuration Status Endpoint
# ---------------------------------------------------------------------------


def test_config_status_endpoint() -> None:
    """GET /v1/config/status returns non-secret configuration status."""
    response = client.get("/v1/config/status")
    assert response.status_code == 200
    data = response.json()
    assert data["environment"] == settings.env
    assert data["demo_mode"] == settings.demo_mode
    assert data["input_mode"] == settings.input_mode
    assert data["database_required"] == settings.database_required
    assert data["expected_database_revision"] == settings.expected_db_revision
    assert "jev_ai" in data
    assert data["jev_ai"]["advisory_only"] is True
    assert data["jev_ai"]["local_only"] is True
    assert data["jev_ai"]["endpoint_label"] == "lm_studio_local"
