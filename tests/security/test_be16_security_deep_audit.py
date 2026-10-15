from __future__ import annotations

import hashlib
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from x_sentinel.audit.evidence import CanonicalEvidence
from x_sentinel.config import settings
from x_sentinel.database.base import Base
from x_sentinel.database.models import JevAIRun, User
from x_sentinel.database.repositories.evidence import CanonicalEvidenceRepository
from x_sentinel.database.repositories.jev_ai import sanitize_error_message
from x_sentinel.database.session import get_db
from x_sentinel.main import app
from x_sentinel.security import (
    PREDEFINED_TOKENS,
    redact_sensitive_dict,
    scan_text_for_secrets,
)

client = TestClient(app)


@pytest.fixture
def sec_db() -> Generator[Session, None, None]:
    """Hermetic SQLite in-memory database fixture for security testing."""
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
def override_db(sec_db: Session) -> Generator[None, None, None]:
    def _get_test_db() -> Generator[Session, None, None]:
        yield sec_db

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestRBACMatrixAndAccessControls:
    """Verifies that role-based access control enforces strict principle of least privilege."""

    @pytest.mark.parametrize(
        "method,endpoint",
        [
            ("POST", "/v1/analyze/vector"),
            ("GET", "/v1/analysis"),
            ("GET", "/v1/alerts"),
            ("GET", "/v1/ai/runs"),
        ],
    )
    def test_anonymous_requests_rejected_when_auth_enabled(
        self, method: str, endpoint: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When static_token auth mode is active, unauthenticated requests return 401."""
        monkeypatch.setattr(settings, "api_auth_mode", "static_token")
        if method == "POST":
            resp = client.post(endpoint, json={"features": [0.0] * 2381})
        else:
            resp = client.get(endpoint)
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] in {"XS_UNAUTHORIZED", "XS_UNAUTHENTICATED"}

    def test_operator_cannot_access_ai_explain(
        self, sec_db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Operator role lacks permissions to trigger advisory AI explain workflows."""
        monkeypatch.setattr(settings, "api_auth_mode", "static_token")
        headers = _auth_headers("token-operator")

        # Create an existing analysis job
        repo = CanonicalEvidenceRepository(sec_db)
        evidence = CanonicalEvidence(
            request_id=f"op-test-{uuid.uuid4()}",
            run_id=f"run-{uuid.uuid4()}",
            timestamp="2026-10-13T12:00:00+00:00",
            code_commit="git_commit_hash_v3_canonical_0002",
            build_digest="sha256:build_digest_x_sentinel_v3_baseline",
            input_id=hashlib.sha256(b"input").hexdigest(),
            input_mode="vector",
            view_map_hash="276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb",
            model_hash="509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2",
            model_config_hash="a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123",
            detector_config_hash="b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123a1",
            seed=42,
            malware_score=0.88,
            signals={"m1": 0.8, "m2": 0.0, "m3": 0.5, "m4": 0.0, "m5": 0.0},
            fusion_score=0.91,
            threshold_id="THRESH-V3-DEFAULT",
            decision="QUARANTINE",
            latency_ms={"end_to_end": 4.5},
            demo_mode=False,
        ).with_hash()
        job, _, _, _, _ = repo.persist(evidence)

        resp = client.post(
            "/v1/ai/explain",
            json={"analysis_id": str(job.id)},
            headers=headers,
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "XS_FORBIDDEN"

    def test_evaluator_role_isolated_from_online_operational_endpoints(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Evaluator role (blind evaluation custody) cannot analyze vectors or view alerts."""
        monkeypatch.setattr(settings, "api_auth_mode", "static_token")
        headers = _auth_headers("token-evaluator")

        resp = client.post(
            "/v1/analyze/vector",
            json={"features": [0.0] * 2381},
            headers=headers,
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "XS_FORBIDDEN"

        resp_alerts = client.get("/v1/alerts", headers=headers)
        assert resp_alerts.status_code == 403
        assert resp_alerts.json()["detail"]["code"] == "XS_FORBIDDEN"


class TestIDORPrevention:
    """Verifies that users cannot access resources belonging to another user."""

    def test_analyst_cannot_view_evidence_owned_by_another_analyst(
        self, sec_db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """User A's canonical evidence cannot be read by User B (IDOR protection)."""
        monkeypatch.setattr(settings, "api_auth_mode", "static_token")
        analyst_a = PREDEFINED_TOKENS["token-analyst"]
        headers_b = _auth_headers("token-analyst-2")
        analyst_b = PREDEFINED_TOKENS["token-analyst-2"]
        sec_db.add(User(id=analyst_a.user_id, email=analyst_a.email, normalized_email=analyst_a.email))
        sec_db.add(User(id=analyst_b.user_id, email=analyst_b.email, normalized_email=analyst_b.email))
        sec_db.flush()

        repo = CanonicalEvidenceRepository(sec_db)
        evidence = CanonicalEvidence(
            request_id=f"idor-test-{uuid.uuid4()}",
            run_id=f"run-{uuid.uuid4()}",
            timestamp="2026-10-13T12:00:00+00:00",
            code_commit="git_commit_hash_v3_canonical_0002",
            build_digest="sha256:build_digest_x_sentinel_v3_baseline",
            input_id=hashlib.sha256(b"input").hexdigest(),
            input_mode="vector",
            view_map_hash="276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb",
            model_hash="509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2",
            model_config_hash="a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123",
            detector_config_hash="b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123a1",
            seed=42,
            malware_score=0.88,
            signals={"m1": 0.8, "m2": 0.0, "m3": 0.5, "m4": 0.0, "m5": 0.0},
            fusion_score=0.91,
            threshold_id="THRESH-V3-DEFAULT",
            decision="QUARANTINE",
            latency_ms={"end_to_end": 4.5},
            demo_mode=False,
        ).with_hash()

        # Job owned by Analyst A
        job, _, _, _, _ = repo.persist(evidence, user_id=analyst_a.user_id)

        # Analyst B attempts to view the analysis record and evidence
        resp = client.get(f"/v1/analysis/{job.id}", headers=headers_b)
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "XS_FORBIDDEN"

        resp_ev = client.get(f"/v1/analysis/{job.id}/evidence", headers=headers_b)
        assert resp_ev.status_code == 403
        assert resp_ev.json()["detail"]["code"] == "XS_FORBIDDEN"

    def test_analyst_cannot_view_ai_run_owned_by_another_analyst(
        self, sec_db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """User B cannot fetch User A's JevAIRun or submit feedback on it."""
        monkeypatch.setattr(settings, "api_auth_mode", "static_token")
        analyst_a = PREDEFINED_TOKENS["token-analyst"]
        analyst_b = PREDEFINED_TOKENS["token-analyst-2"]
        headers_b = _auth_headers("token-analyst-2")
        if sec_db.get(User, analyst_a.user_id) is None:
            sec_db.add(User(id=analyst_a.user_id, email=analyst_a.email, normalized_email=analyst_a.email))
        if sec_db.get(User, analyst_b.user_id) is None:
            sec_db.add(User(id=analyst_b.user_id, email=analyst_b.email, normalized_email=analyst_b.email))
        sec_db.flush()

        run = JevAIRun(
            mode="explain",
            status="completed",
            model_id="test-model",
            requested_by_user_id=analyst_a.user_id,
            prompt_version="1.0.0",
            input_digest_sha256=hashlib.sha256(b"in").hexdigest(),
            output_digest_sha256=hashlib.sha256(b"out").hexdigest(),
            response_text="Sensitive analysis owned by Analyst A",
        )
        sec_db.add(run)
        sec_db.commit()
        sec_db.refresh(run)

        # Analyst B attempts to read AI run
        resp = client.get(f"/v1/ai/runs/{run.id}", headers=headers_b)
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "XS_FORBIDDEN"

        # Analyst B attempts to submit feedback
        resp_fb = client.post(
            f"/v1/ai/runs/{run.id}/feedback",
            json={"rating": 5, "label": "helpful"},
            headers=headers_b,
        )
        assert resp_fb.status_code == 403
        assert resp_fb.json()["detail"]["code"] == "XS_FORBIDDEN"


class TestSecretSanitizationAndRedaction:
    """Verifies that secrets, database credentials, and internal paths are never leaked."""

    def test_database_password_and_url_redacted(self) -> None:
        """Sanitizer scrubs database connection strings and passwords."""
        leak_string = (
            "Internal DB error: mssql+pyodbc://sa:SuperSecretPassword123!@localhost:1433/xsentinel"
        )
        sanitized = sanitize_error_message(leak_string)
        assert sanitized is not None
        assert "SuperSecretPassword123!" not in sanitized
        assert "password" not in sanitized.lower() or "[REDACTED]" in sanitized

    def test_secret_scanner_detects_embedded_keys(self) -> None:
        """scan_text_for_secrets flags potential API keys or private tokens with correct metadata."""
        # Construct credentials dynamically at runtime to avoid static false positives in repo scans
        raw_aws = "AKIA" + "1" * 16
        raw_db = "postgres://" + "dbuser:super_secret_db_pass123!@localhost:5432/production_db"
        sample_with_key = f"AWS_KEY_ID={raw_aws}\nDB_PASS={raw_db}"
        findings = scan_text_for_secrets(sample_with_key)
        assert len(findings) >= 2
        detected_types = {f.secret_type for f in findings}
        assert "AWS_KEY" in detected_types
        assert "DB_CONNECTION_PASSWORD" in detected_types
        for f in findings:
            assert f.severity == "P0_CRITICAL"
            assert "***REDACTED***" in f.masked_snippet

    def test_secret_scanner_ignores_synthetic_whitelist_tokens(self) -> None:
        """Synthetic tokens like token-admin or placeholder are whitelisted and produce zero findings."""
        sample_synthetic = "Authorization: Bearer token-admin\npassword = 'change_me'"
        findings = scan_text_for_secrets(sample_synthetic, ignore_synthetic=True)
        assert len(findings) == 0

    def test_redact_sensitive_dict_scrubs_nested_secrets(self) -> None:
        """Dictionary redactor masks sensitive keys at all levels."""
        data = {
            "user": "analyst",
            "password": "PlaintextPassword",
            "api_key": "secret-1234",
            "nested": {
                "token": "bearer-token-val",
                "normal": "safe_value",
            },
        }
        redacted = redact_sensitive_dict(data)
        assert redacted["password"] == "[REDACTED]"
        assert redacted["api_key"] == "[REDACTED]"
        assert redacted["nested"]["token"] == "[REDACTED]"
        assert redacted["nested"]["normal"] == "safe_value"
