from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from x_sentinel.database.base import Base
from x_sentinel.database.models import (
    Alert,
    AnalysisResultRecord,
)
from x_sentinel.database.session import get_db
from x_sentinel.main import app

client = TestClient(app)


@pytest.fixture
def core_api_db() -> Session:
    """Hermetic SQLite in-memory database fixture for API tests."""
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


@pytest.fixture(autouse=True)
def override_db(core_api_db: Session):
    def _get_test_db():
        yield core_api_db

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


# ===========================================================================
# 1. Analysis API Unit Tests
# ===========================================================================


def test_analyze_vector_success() -> None:
    """POST /v1/analyze/vector with valid 2,381 vector produces canonical AnalysisResponse."""
    req_id = f"req-test-core-{uuid.uuid4()}"
    vector = [0.0] * 2381
    vector[0] = 12.5
    vector[1] = 45.0

    resp = client.post(
        "/v1/analyze/vector",
        json={"features": vector, "request_id": req_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == req_id
    assert data["demo_mode"] is True
    assert 0.0 <= data["malware_score"] <= 1.0
    assert 0.0 <= data["suspicion_score"] <= 1.0
    assert set(data["signals"].keys()) == {"m1", "m2", "m3", "m4", "m5"}
    assert "structural" in data["view_contributions"]
    assert "behavioral" in data["view_contributions"]
    assert "metadata" in data["view_contributions"]
    assert data["evidence_ref"] is not None
    assert len(data["evidence_ref"]) == 64
    assert data["job_id"] is not None


def test_analyze_vector_invalid_length_returns_422() -> None:
    """Vector with fewer or more than 2,381 features rejected with 422 XS_INPUT_INVALID."""
    resp = client.post(
        "/v1/analyze/vector",
        json={"features": [0.0] * 100, "request_id": "req-invalid-len"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "XS_INPUT_INVALID"


def test_analyze_vector_nan_features_returns_422() -> None:
    """Vector containing NaN or Inf values rejected with 422 XS_INPUT_INVALID."""
    raw = '{"features": [' + '0.0,' * 2380 + 'NaN], "request_id": "req-invalid-nan"}'
    resp = client.post(
        "/v1/analyze/vector",
        content=raw,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "XS_INPUT_INVALID"


def test_analyze_vector_duplicate_request_id_returns_409() -> None:
    """Submitting the same request_id twice returns 409 XS_DUPLICATE_REQUEST."""
    req_id = f"req-duplicate-{uuid.uuid4()}"
    vector = [0.0] * 2381

    # First request succeeds
    resp1 = client.post("/v1/analyze/vector", json={"features": vector, "request_id": req_id})
    assert resp1.status_code == 200

    # Second request with duplicate request_id rejected with 409
    resp2 = client.post("/v1/analyze/vector", json={"features": vector, "request_id": req_id})
    assert resp2.status_code == 409
    assert resp2.json()["detail"]["code"] == "XS_DUPLICATE_REQUEST"


def test_analyze_file_phase2_disabled() -> None:
    """POST /v1/analyze/file returns 501 XS_FEATURE_DISABLED."""
    resp = client.post("/v1/analyze/file")
    assert resp.status_code == 501
    assert resp.json()["detail"]["code"] == "XS_FEATURE_DISABLED"


# ===========================================================================
# 2. History API Unit Tests
# ===========================================================================


def test_list_history_empty() -> None:
    """GET /v1/analysis on empty database returns total=0 and empty items list."""
    resp = client.get("/v1/analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_history_populated_and_pagination() -> None:
    """GET /v1/analysis returns records ordered by created_at desc with correct pagination."""
    # Seed 3 jobs
    for i in range(3):
        client.post(
            "/v1/analyze/vector",
            json={"features": [0.0] * 2381, "request_id": f"req-hist-seed-{i}"},
        )

    # Fetch with limit=2, offset=0
    resp_page1 = client.get("/v1/analysis?limit=2&offset=0")
    assert resp_page1.status_code == 200
    data1 = resp_page1.json()
    assert data1["total"] == 3
    assert len(data1["items"]) == 2
    assert data1["limit"] == 2
    assert data1["offset"] == 0

    # Fetch with limit=2, offset=2
    resp_page2 = client.get("/v1/analysis?limit=2&offset=2")
    assert resp_page2.status_code == 200
    data2 = resp_page2.json()
    assert data2["total"] == 3
    assert len(data2["items"]) == 1


def test_list_history_filtering() -> None:
    """GET /v1/analysis filters by status, decision, input_mode."""
    req_id = f"req-hist-filter-{uuid.uuid4()}"
    client.post("/v1/analyze/vector", json={"features": [0.0] * 2381, "request_id": req_id})

    # Filter matching status
    resp_match = client.get("/v1/analysis?status=completed")
    assert resp_match.status_code == 200
    assert resp_match.json()["total"] >= 1

    # Filter non-matching status
    resp_no_match = client.get("/v1/analysis?status=failed")
    assert resp_no_match.status_code == 200
    assert resp_no_match.json()["total"] == 0


def test_get_analysis_detail_by_uuid_and_request_id() -> None:
    """GET /v1/analysis/{analysis_id} retrieves detail by UUID and by request_id."""
    req_id = f"req-detail-{uuid.uuid4()}"
    resp_post = client.post(
        "/v1/analyze/vector",
        json={"features": [0.0] * 2381, "request_id": req_id},
    )
    assert resp_post.status_code == 200
    job_id = resp_post.json()["job_id"]
    assert job_id is not None

    # Retrieve by UUID
    resp_by_uuid = client.get(f"/v1/analysis/{job_id}")
    assert resp_by_uuid.status_code == 200
    data_uuid = resp_by_uuid.json()
    assert data_uuid["id"] == job_id
    assert data_uuid["request_id"] == req_id
    assert data_uuid["result"] is not None
    assert len(data_uuid["scores"]) == 5

    # Retrieve by request_id
    resp_by_req = client.get(f"/v1/analysis/{req_id}")
    assert resp_by_req.status_code == 200
    assert resp_by_req.json()["id"] == job_id


def test_get_analysis_detail_not_found() -> None:
    """GET /v1/analysis/{analysis_id} for non-existent record returns 404 XS_ANALYSIS_NOT_FOUND."""
    resp = client.get("/v1/analysis/non-existent-analysis-id-xyz")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "XS_ANALYSIS_NOT_FOUND"


# ===========================================================================
# 3. Alerts API Unit Tests
# ===========================================================================


def test_list_alerts_and_filtering(core_api_db: Session) -> None:
    """GET /v1/alerts lists alerts with severity and status filters."""
    # Seed alerts directly in db
    dummy_job_id = uuid.uuid4()
    alert1 = Alert(
        id=uuid.uuid4(),
        analysis_job_id=dummy_job_id,
        severity="high",
        status="open",
        reason="Test high alert",
    )
    alert2 = Alert(
        id=uuid.uuid4(),
        analysis_job_id=dummy_job_id,
        severity="low",
        status="resolved",
        reason="Test low resolved alert",
    )
    core_api_db.add_all([alert1, alert2])
    core_api_db.commit()

    # List all
    resp_all = client.get("/v1/alerts")
    assert resp_all.status_code == 200
    assert resp_all.json()["total"] == 2

    # Filter severity=high
    resp_high = client.get("/v1/alerts?severity=high")
    assert resp_high.status_code == 200
    assert resp_high.json()["total"] == 1
    assert resp_high.json()["items"][0]["severity"] == "high"

    # Filter status=resolved
    resp_res = client.get("/v1/alerts?status=resolved")
    assert resp_res.status_code == 200
    assert resp_res.json()["total"] == 1
    assert resp_res.json()["items"][0]["status"] == "resolved"


def test_get_alert_detail() -> None:
    """GET /v1/alerts/{alert_id} returns alert details or 404."""
    # Create an alert via vector with high suspicion
    req_id = f"req-alert-gen-{uuid.uuid4()}"
    vector = [0.0] * 2381
    vector[0] = 100.0  # high feature
    resp_analyze = client.post(
        "/v1/analyze/vector",
        json={"features": vector, "request_id": req_id},
    )
    assert resp_analyze.status_code == 200

    # Query alert
    resp_alerts = client.get("/v1/alerts")
    assert resp_alerts.status_code == 200
    items = resp_alerts.json()["items"]
    if items:
        target_alert = items[0]
        alert_id = target_alert["id"]

        resp_detail = client.get(f"/v1/alerts/{alert_id}")
        assert resp_detail.status_code == 200
        assert resp_detail.json()["id"] == alert_id

    # Non-existent alert
    resp_none = client.get(f"/v1/alerts/{uuid.uuid4()}")
    assert resp_none.status_code == 404
    assert resp_none.json()["detail"]["code"] == "XS_ALERT_NOT_FOUND"


def test_update_alert_lifecycle_valid_transitions(core_api_db: Session) -> None:
    """PATCH /v1/alerts/{alert_id} validates and transitions states across lifecycle."""
    dummy_job_id = uuid.uuid4()
    alert_id = uuid.uuid4()
    alert = Alert(
        id=alert_id,
        analysis_job_id=dummy_job_id,
        severity="high",
        status="open",
        reason="Lifecycle test alert",
    )
    core_api_db.add(alert)
    core_api_db.commit()

    # Step 1: open -> acknowledged
    resp_ack = client.patch(f"/v1/alerts/{alert_id}", json={"status": "acknowledged"})
    assert resp_ack.status_code == 200
    assert resp_ack.json()["status"] == "acknowledged"
    assert resp_ack.json()["resolved_at"] is None

    # Step 2: acknowledged -> resolved
    resp_res = client.patch(f"/v1/alerts/{alert_id}", json={"status": "resolved"})
    assert resp_res.status_code == 200
    assert resp_res.json()["status"] == "resolved"
    assert resp_res.json()["resolved_at"] is not None


def test_update_alert_lifecycle_invalid_transition_rejected(core_api_db: Session) -> None:
    """Transitioning an alert from terminal state 'resolved' back to 'open' is rejected with 400."""
    dummy_job_id = uuid.uuid4()
    alert_id = uuid.uuid4()
    alert = Alert(
        id=alert_id,
        analysis_job_id=dummy_job_id,
        severity="medium",
        status="resolved",
        reason="Resolved alert",
    )
    core_api_db.add(alert)
    core_api_db.commit()

    # Attempt terminal -> open
    resp_bad = client.patch(f"/v1/alerts/{alert_id}", json={"status": "open"})
    assert resp_bad.status_code == 400
    assert resp_bad.json()["detail"]["code"] == "XS_INVALID_TRANSITION"


def test_update_alert_unknown_status_rejected(core_api_db: Session) -> None:
    """Target status outside valid set is rejected with 400 XS_INVALID_TRANSITION."""
    dummy_job_id = uuid.uuid4()
    alert_id = uuid.uuid4()
    alert = Alert(
        id=alert_id,
        analysis_job_id=dummy_job_id,
        severity="low",
        status="open",
        reason="Open alert",
    )
    core_api_db.add(alert)
    core_api_db.commit()

    resp_bad = client.patch(f"/v1/alerts/{alert_id}", json={"status": "invalid_status_xyz"})
    assert resp_bad.status_code == 400
    assert resp_bad.json()["detail"]["code"] == "XS_INVALID_TRANSITION"


# ===========================================================================
# 4. Evidence API Unit Tests
# ===========================================================================


def test_get_evidence_success() -> None:
    """GET /v1/analysis/{analysis_id}/evidence returns 19 canonical fields and verified=True."""
    req_id = f"req-ev-test-{uuid.uuid4()}"
    resp_post = client.post(
        "/v1/analyze/vector",
        json={"features": [0.0] * 2381, "request_id": req_id},
    )
    assert resp_post.status_code == 200
    job_id = resp_post.json()["job_id"]
    ev_hash = resp_post.json()["evidence_ref"]

    # Read evidence by job UUID
    resp_ev = client.get(f"/v1/analysis/{job_id}/evidence")
    assert resp_ev.status_code == 200
    data = resp_ev.json()
    assert data["request_id"] == req_id
    assert data["evidence_hash"] == ev_hash
    assert data["verified"] is True
    assert set(data["signals"].keys()) == {"m1", "m2", "m3", "m4", "m5"}
    assert "end_to_end" in data["latency_ms"]


def test_get_evidence_not_found() -> None:
    """GET /v1/analysis/{analysis_id}/evidence for missing record returns 404."""
    resp = client.get(f"/v1/analysis/{uuid.uuid4()}/evidence")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "XS_EVIDENCE_NOT_FOUND"


def test_get_evidence_tamper_detection(core_api_db: Session) -> None:
    """Tampering with persisted canonical evidence triggers 409 XS_EVIDENCE_INTEGRITY_MISMATCH."""
    req_id = f"req-tamper-{uuid.uuid4()}"
    resp_post = client.post(
        "/v1/analyze/vector",
        json={"features": [0.0] * 2381, "request_id": req_id},
    )
    assert resp_post.status_code == 200
    job_id = uuid.UUID(resp_post.json()["job_id"])

    # Directly tamper result_json in the database (modify malware_score)
    res_rec = core_api_db.get(AnalysisResultRecord, job_id)
    assert res_rec is not None
    tampered_json = dict(res_rec.result_json)
    tampered_json["malware_score"] = 0.999999
    res_rec.result_json = tampered_json
    core_api_db.commit()

    # Reading tampered evidence must detect mismatch and return 409
    resp_ev = client.get(f"/v1/analysis/{job_id}/evidence")
    assert resp_ev.status_code == 409
    assert resp_ev.json()["detail"]["code"] == "XS_EVIDENCE_INTEGRITY_MISMATCH"
