from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from x_sentinel.database.base import Base
from x_sentinel.database.session import get_db
from x_sentinel.main import app

client = TestClient(app)


@pytest.fixture
def contract_db() -> Generator[Session, None, None]:
    """Hermetic SQLite in-memory database fixture for contract testing."""
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
            default_arg = getattr(col.server_default, "arg", None)
            if default_arg is not None:
                text_str = str(default_arg)
                if "N'" in text_str and hasattr(default_arg, "text"):
                    default_arg.text = text_str.replace("N'", "'")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def override_db(contract_db: Session) -> Generator[None, None, None]:
    def _get_test_db() -> Generator[Session, None, None]:
        yield contract_db

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


class TestOpenAPIContractCompliance:
    """Verifies that the API matches the frozen OpenAPI specification exactly."""

    def test_openapi_schema_contains_required_endpoints(self) -> None:
        """All 16+ production endpoints must be documented in OpenAPI schema."""
        schema = app.openapi()
        paths = schema.get("paths", {})

        expected = [
            "/health",
            "/ready",
            "/v1/config/status",
            "/v1/ai/status",
            "/v1/analyze/vector",
            "/v1/analysis",
            "/v1/analysis/{analysis_id}",
            "/v1/analysis/{analysis_id}/evidence",
            "/v1/alerts",
            "/v1/alerts/{alert_id}",
            "/v1/ai/explain",
            "/v1/ai/runs",
            "/v1/ai/runs/{run_id}",
            "/v1/ai/runs/{run_id}/feedback",
        ]
        for path in expected:
            assert path in paths, f"Path '{path}' missing from OpenAPI specification"

    def test_all_responses_use_application_json(self) -> None:
        """Every endpoint returns Content-Type application/json; zero Jinja/HTML templates."""
        endpoints = [
            "/health",
            "/ready",
            "/v1/config/status",
            "/v1/ai/status",
            "/v1/analysis",
            "/v1/alerts",
            "/v1/ai/runs",
        ]
        for endpoint in endpoints:
            resp = client.get(endpoint)
            ct = resp.headers.get("content-type", "")
            assert "application/json" in ct, f"Endpoint '{endpoint}' returned non-JSON content-type: {ct}"
            assert not ct.startswith("text/html"), f"Endpoint '{endpoint}' illegally returned HTML"

    def test_nonexistent_route_returns_json_404(self) -> None:
        """404 responses return JSON error envelope rather than HTML error page."""
        resp = client.get(f"/v1/non_existent_route_{uuid.uuid4()}")
        assert resp.status_code == 404
        assert "application/json" in resp.headers.get("content-type", "")


class TestErrorEnvelopeContract:
    """Verifies consistent {"detail": {"code": ..., "message": ...}} error contracts."""

    def test_422_input_validation_envelope_structure(self) -> None:
        """Validation errors follow canonical XS_INPUT_INVALID error envelope."""
        resp = client.post("/v1/analyze/vector", json={"features": [1.0, 2.0]})
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body
        assert isinstance(body["detail"], dict)
        assert "code" in body["detail"]
        assert "message" in body["detail"]
        assert body["detail"]["code"] == "XS_INPUT_INVALID"

    def test_404_resource_not_found_envelope_structure(self) -> None:
        """Resource lookups follow canonical not found error envelope."""
        random_id = str(uuid.uuid4())
        resp = client.get(f"/v1/analysis/{random_id}")
        assert resp.status_code == 404
        body = resp.json()
        assert "detail" in body
        assert isinstance(body["detail"], dict)
        assert body["detail"]["code"] == "XS_ANALYSIS_NOT_FOUND"
        assert "message" in body["detail"]

    def test_404_evidence_not_found_envelope_structure(self) -> None:
        """Evidence not found returns XS_EVIDENCE_NOT_FOUND error code."""
        random_id = str(uuid.uuid4())
        resp = client.get(f"/v1/analysis/{random_id}/evidence")
        assert resp.status_code == 404
        body = resp.json()
        assert body["detail"]["code"] == "XS_EVIDENCE_NOT_FOUND"


class TestVectorAnalysisBackwardCompatibility:
    """Verifies vector analysis endpoint payload compatibility."""

    def test_vector_analysis_successful_response_fields(self) -> None:
        """2,381 feature vector request returns full canonical decision structure."""
        req_id = f"contract-req-{uuid.uuid4()}"
        resp = client.post(
            "/v1/analyze/vector",
            json={
                "features": [0.0] * 2381,
                "request_id": req_id,
                "demo_mode": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        # Check required fields in AnalysisResponse
        assert data["request_id"] == req_id
        assert data["status"] in {"completed", "quarantined", "DEMO_ONLY"}
        assert data["decision"] in {"pass", "alert", "quarantine", "PASS", "ALERT", "QUARANTINE"}
        assert isinstance(data["malware_score"], (int, float))
        assert isinstance(data["suspicion_score"], (int, float))
        assert isinstance(data["threshold"], (int, float))
        assert "signals" in data
        assert isinstance(data["signals"], dict)
        assert "evidence_ref" in data
        assert len(data["evidence_ref"]) == 64
        assert "view_contributions" in data
