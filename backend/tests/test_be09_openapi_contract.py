from __future__ import annotations

from pathlib import Path

import yaml
from fastapi.testclient import TestClient
from x_sentinel.main import app

client = TestClient(app)


def test_openapi_schema_generation() -> None:
    """Acceptance Criterion 1: OpenAPI schema generates cleanly without errors."""
    schema = app.openapi()
    assert schema is not None
    assert schema["openapi"] == "3.1.0"
    assert schema["info"]["title"] == "X-SENTINEL"
    assert "paths" in schema
    assert "components" in schema


def test_openapi_registered_endpoints() -> None:
    """Verify that all canonical BE-09 and baseline endpoints are registered."""
    schema = app.openapi()
    paths = schema["paths"]

    expected_endpoints = {
        "/health": ["get"],
        "/ready": ["get"],
        "/v1/config/status": ["get"],
        "/v1/ai/status": ["get"],
        "/v1/ai/explain": ["post"],
        "/v1/ai/runs": ["get"],
        "/v1/ai/runs/{run_id}": ["get"],
        "/v1/ai/runs/{run_id}/feedback": ["post", "get"],
        "/v1/ai/docs/ask": ["post"],
        "/v1/analyze/vector": ["post"],
        "/v1/analyze/file": ["post"],
        "/v1/analysis": ["get"],
        "/v1/analysis/{analysis_id}": ["get"],
        "/v1/analysis/{analysis_id}/evidence": ["get"],
        "/v1/alerts": ["get"],
        "/v1/alerts/{alert_id}": ["get", "patch"],
    }

    for path, methods in expected_endpoints.items():
        assert path in paths, f"Expected path '{path}' missing from OpenAPI schema!"
        for method in methods:
            assert method in paths[path], f"Expected method '{method.upper()}' missing for '{path}'"


def test_openapi_components_schemas_present() -> None:
    """Verify that all canonical Pydantic request/response models exist in components.schemas."""
    schema = app.openapi()
    schemas = schema["components"]["schemas"]

    expected_schemas = [
        "VectorAnalysisRequest",
        "AnalysisResponse",
        "AnalysisJobSummary",
        "AnalysisHistoryListResponse",
        "AnalysisDetailResponse",
        "AlertSummary",
        "AlertListResponse",
        "AlertStatusUpdateRequest",
        "CanonicalEvidenceResponse",
        "DetectorScoreItem",
        "JevStatusResponse",
        "JevExplainRequest",
        "JevAIRunResponse",
        "JevAIRunListResponse",
        "JevFeedbackRequest",
        "JevFeedbackResponse",
        "JevFeedbackListResponse",
    ]

    for model_name in expected_schemas:
        assert model_name in schemas, f"Schema '{model_name}' missing from OpenAPI schemas!"


def test_openapi_security_schemes() -> None:
    """Verify HTTPBearer security scheme definition."""
    schema = app.openapi()
    security_schemes = schema["components"].get("securitySchemes", {})
    assert "HTTPBearer" in security_schemes
    assert security_schemes["HTTPBearer"]["type"] == "http"
    assert security_schemes["HTTPBearer"]["scheme"] == "bearer"


def test_openapi_operation_ids_unique() -> None:
    """Verify that every operation across all endpoints has a unique operationId."""
    schema = app.openapi()
    op_ids: set[str] = set()
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if isinstance(operation, dict) and "operationId" in operation:
                op_id = operation["operationId"]
                msg = f"Duplicate operationId '{op_id}' in {method.upper()} {path}"
                assert op_id not in op_ids, msg
                op_ids.add(op_id)


def test_openapi_matches_yaml_contract() -> None:
    """Verify that docs/api/openapi.yaml matches the current application schema."""
    yaml_path = Path("docs/api/openapi.yaml")
    assert yaml_path.exists(), "docs/api/openapi.yaml must exist on disk"

    stored_yaml = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    live_schema = app.openapi()

    assert stored_yaml["openapi"] == live_schema["openapi"]
    assert stored_yaml["info"]["title"] == live_schema["info"]["title"]
    assert set(stored_yaml["paths"].keys()) == set(live_schema["paths"].keys())
    stored_schemas = set(stored_yaml["components"]["schemas"].keys())
    live_schemas = set(live_schema["components"]["schemas"].keys())
    assert stored_schemas == live_schemas


def test_openapi_endpoint_status_codes_documented() -> None:
    """Verify documented responses on critical analysis, history, alerts, and evidence endpoints."""
    schema = app.openapi()
    paths = schema["paths"]

    # /v1/analyze/vector documents 200 and 422
    vec_path = paths["/v1/analyze/vector"]
    assert "200" in vec_path["post"]["responses"]
    assert "422" in vec_path["post"]["responses"]

    # /v1/analysis documents 200
    assert "200" in paths["/v1/analysis"]["get"]["responses"]

    # /v1/analysis/{analysis_id} documents 200
    assert "200" in paths["/v1/analysis/{analysis_id}"]["get"]["responses"]

    # /v1/alerts documents 200
    assert "200" in paths["/v1/alerts"]["get"]["responses"]

    # /v1/alerts/{alert_id} documents 200 for GET and PATCH
    assert "200" in paths["/v1/alerts/{alert_id}"]["get"]["responses"]
    assert "200" in paths["/v1/alerts/{alert_id}"]["patch"]["responses"]
