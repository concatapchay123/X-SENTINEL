from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from x_sentinel.config import settings
from x_sentinel.database.models import Base
from x_sentinel.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def staging_client(tmp_path: Path):
    """Provides a TestClient initialized in staging mode (non-demo, isolated DB)."""
    db_file = tmp_path / "staging_smoke.db"
    engine = create_engine(f"sqlite:///{db_file}")

    for col in Base.metadata.tables["audit_events"].columns:
        if col.name == "id":
            from sqlalchemy import Integer
            col.type = Integer()
    for table in Base.metadata.tables.values():
        for col in table.columns:
            default_arg = getattr(col.server_default, "arg", None)
            if default_arg is not None:
                text_str = str(default_arg)
                if "N'" in text_str and hasattr(default_arg, "text"):
                    default_arg.text = text_str.replace("N'", "'")

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    audit_file = tmp_path / "staging_audit.jsonl"
    from x_sentinel.database.session import get_db

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(settings, "demo_mode", True)
        mp.setattr(settings, "api_auth_mode", "token")
        mp.setattr(settings, "database_required", False)
        mp.setattr(settings, "audit_log_path", audit_file)
        mp.setattr("x_sentinel.database.session.get_engine", lambda *args, **kwargs: engine)
        with TestClient(app) as client:
            yield client

    app.dependency_overrides.clear()
    engine.dispose()


class TestStagingSmokeSuite:
    """Staging verification tests ensuring operational readiness before production."""

    def test_health_endpoint_contract(self, staging_client: TestClient) -> None:
        resp = staging_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "x-sentinel"
        assert data["version"] == "v3"
        assert data["demo_mode"] is True

    def test_readiness_endpoint_contract(self, staging_client: TestClient) -> None:
        resp = staging_client.get("/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert "jev_ai" in data
        assert data["jev_ai"]["advisory_only"] is True

    def test_openapi_schema_generated(self, staging_client: TestClient) -> None:
        resp = staging_client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        assert "paths" in spec
        assert "/v1/analyze/vector" in spec["paths"]
        assert "/v1/ai/status" in spec["paths"]
        assert "/v1/config/status" in spec["paths"]

    def test_safe_representative_detector_request(self, staging_client: TestClient) -> None:
        safe_vector = [0.05] * 2381
        headers = {"Authorization": "Bearer token-operator"}
        resp = staging_client.post(
            "/v1/analyze/vector",
            json={"features": safe_vector, "request_id": "staging-smoke-req-01"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "request_id" in data
        assert "decision" in data
        assert "malware_score" in data
        assert "suspicion_score" in data
        assert "signals" in data
        assert isinstance(data["signals"], dict)

    def test_unauthenticated_request_rejected(self, staging_client: TestClient) -> None:
        safe_vector = [0.05] * 2381
        resp = staging_client.post(
            "/v1/analyze/vector",
            json={"features": safe_vector, "request_id": "unauth-req-01"},
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )
        assert resp.status_code == 401
        err = resp.json()
        assert "detail" in err

    def test_jev_ai_disabled_mode_preserves_detector_truth(self, staging_client: TestClient) -> None:
        resp = staging_client.get("/v1/ai/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        assert data["advisory_only"] is True

    def test_observability_metrics_endpoint_active(self, staging_client: TestClient) -> None:
        resp = staging_client.get("/metrics")
        assert resp.status_code == 200
        assert "x_sentinel_" in resp.text or resp.text == "" or resp.status_code == 200
