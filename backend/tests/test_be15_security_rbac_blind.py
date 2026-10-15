from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from x_sentinel.config import settings
from x_sentinel.database.base import Base
from x_sentinel.database.models import AnalysisJob
from x_sentinel.database.session import get_db
from x_sentinel.evaluation.blind import (
    BlindCustodyGuard,
    BlindEvaluator,
    BlindGroundTruthManifest,
    BlindLabelLeakageError,
    BlindPredictionPackage,
    BlindSamplePrediction,
    EvaluationRole,
    ForbiddenEnvironmentExposureError,
    ManifestAccessDeniedError,
    PostHocTuningForbiddenError,
)
from x_sentinel.main import app
from x_sentinel.security import (
    PREDEFINED_TOKENS,
    AuthUser,
    PathTraversalAttemptError,
    Role,
    assert_jev_ai_safe_from_blind_data,
    assert_path_safe_from_traversal,
    record_security_event,
    redact_sensitive_dict,
    redact_sensitive_text,
    scan_directory_for_secrets,
    scan_text_for_secrets,
    verify_database_manifest_isolation,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def be15_db() -> Session:
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


# ===========================================================================
# 1. NEGATIVE AUTHORIZATION & RBAC TESTS (GATES C & D)
# ===========================================================================


class TestNegativeAuthorizationAndRBAC:
    def test_unauthenticated_requests_rejected_401_when_auth_enabled(self) -> None:
        """When api_auth_mode == 'bearer', requests missing Authorization header return 401."""
        with patch.object(settings, "api_auth_mode", "bearer"):
            endpoints = [
                ("GET", "/v1/analysis"),
                ("GET", "/v1/analysis/some-id"),
                ("GET", "/v1/analysis/some-id/evidence"),
                ("GET", "/v1/alerts"),
                ("GET", "/v1/alerts/some-id"),
                ("PATCH", "/v1/alerts/some-id"),
                ("POST", "/v1/analyze/vector"),
                ("POST", "/v1/ai/explain"),
                ("GET", "/v1/ai/runs"),
                ("GET", "/v1/ai/runs/some-id"),
                ("POST", "/v1/ai/runs/some-id/feedback"),
                ("GET", "/v1/ai/runs/some-id/feedback"),
            ]
            for method, path in endpoints:
                if method == "GET":
                    resp = client.get(path)
                elif method == "POST":
                    resp = client.post(path, json={})
                elif method == "PATCH":
                    resp = client.patch(path, json={})
                assert resp.status_code == 401, f"Failed on {method} {path}"
                assert resp.json()["detail"]["code"] == "XS_UNAUTHENTICATED"

    def test_invalid_or_forged_bearer_token_rejected_401(self) -> None:
        """When api_auth_mode == 'bearer', forged tokens return 401 XS_INVALID_CREDENTIALS."""
        with patch.object(settings, "api_auth_mode", "bearer"):
            forged_tokens = [
                "forged-token-xyz",
                "bearer token-admin",
                "token-superadmin",
                "Bearer invalid.jwt.signature",
            ]
            for tok in forged_tokens:
                headers = {"Authorization": f"Bearer {tok}"}
                resp = client.get("/v1/analysis", headers=headers)
                assert resp.status_code == 401
                assert resp.json()["detail"]["code"] == "XS_INVALID_CREDENTIALS"

    def test_inactive_user_account_rejected_403(self) -> None:
        """When an account is flagged inactive, access is forbidden with 403 XS_FORBIDDEN."""
        with patch.object(settings, "api_auth_mode", "bearer"):
            headers = {"Authorization": "Bearer token-inactive"}
            resp = client.get("/v1/analysis", headers=headers)
            assert resp.status_code == 403
            assert resp.json()["detail"]["code"] == "XS_FORBIDDEN"
            assert "inactive" in resp.json()["detail"]["message"].lower()

    def test_operator_forbidden_from_evidence_and_alert_mutation_403(
        self, be15_db: Session
    ) -> None:
        """Operator role cannot read canonical evidence or mutate alert statuses."""

        def override_db():
            yield be15_db

        app.dependency_overrides[get_db] = override_db
        try:
            with patch.object(settings, "api_auth_mode", "bearer"):
                op_headers = {"Authorization": "Bearer token-operator"}

                # Operator cannot read evidence
                resp_ev = client.get("/v1/analysis/job-01/evidence", headers=op_headers)
                assert resp_ev.status_code == 403
                assert resp_ev.json()["detail"]["code"] == "XS_FORBIDDEN"

                # Operator cannot patch alerts
                resp_patch = client.patch(
                    "/v1/alerts/some-alert",
                    json={"status": "resolved"},
                    headers=op_headers,
                )
                assert resp_patch.status_code == 403
                assert resp_patch.json()["detail"]["code"] == "XS_FORBIDDEN"
        finally:
            app.dependency_overrides.clear()

    def test_evaluator_forbidden_from_submitting_vector_analysis_403(
        self, be15_db: Session
    ) -> None:
        """Evaluator role cannot execute live vector analysis."""

        def override_db():
            yield be15_db

        app.dependency_overrides[get_db] = override_db
        try:
            with patch.object(settings, "api_auth_mode", "bearer"):
                eval_headers = {"Authorization": "Bearer token-evaluator"}
                resp = client.post(
                    "/v1/analyze/vector",
                    json={"features": [0.0] * 2381, "request_id": "eval-forbidden-req"},
                    headers=eval_headers,
                )
                assert resp.status_code == 403
                assert resp.json()["detail"]["code"] == "XS_FORBIDDEN"
        finally:
            app.dependency_overrides.clear()

    def test_operator_and_evaluator_forbidden_from_jev_ai_workflows_403(self) -> None:
        """Operator and Evaluator cannot invoke Jev AI workflows or submit feedback."""
        with patch.object(settings, "api_auth_mode", "bearer"):
            for tok in ("token-operator", "token-evaluator"):
                headers = {"Authorization": f"Bearer {tok}"}
                resp_explain = client.post(
                    "/v1/ai/explain",
                    json={"analysis_id": str(uuid.uuid4()), "mode": "explain"},
                    headers=headers,
                )
                assert resp_explain.status_code == 403
                assert resp_explain.json()["detail"]["code"] == "XS_FORBIDDEN"

                resp_fb = client.post(
                    f"/v1/ai/runs/{uuid.uuid4()}/feedback",
                    json={"rating": 5, "label": "helpful"},
                    headers=headers,
                )
                assert resp_fb.status_code == 403
                assert resp_fb.json()["detail"]["code"] == "XS_FORBIDDEN"

    def test_client_cannot_forge_roles_via_request_headers(self, be15_db: Session) -> None:
        """Injecting custom role headers like X-Role, Role, X-Is-Admin does not bypass RBAC."""

        def override_db():
            yield be15_db

        app.dependency_overrides[get_db] = override_db
        try:
            with patch.object(settings, "api_auth_mode", "bearer"):
                forged_headers = {
                    "Authorization": "Bearer token-operator",
                    "X-Role": "admin",
                    "X-User-Role": "admin",
                    "Role": "admin",
                    "X-Is-Admin": "true",
                }
                resp = client.patch(
                    "/v1/alerts/some-alert",
                    json={"status": "resolved"},
                    headers=forged_headers,
                )
                assert resp.status_code == 403
                assert resp.json()["detail"]["code"] == "XS_FORBIDDEN"
        finally:
            app.dependency_overrides.clear()

    def test_mass_assignment_extra_fields_cannot_escalate_privilege(self, be15_db: Session) -> None:
        """Sending extra unapproved fields in analysis request cannot alter user_id or decision."""

        def override_db():
            yield be15_db

        app.dependency_overrides[get_db] = override_db
        try:
            with patch.object(settings, "api_auth_mode", "bearer"):
                analyst_headers = {"Authorization": "Bearer token-analyst"}
                fake_victim_user_id = str(uuid.UUID("99999999-9999-9999-9999-999999999999"))
                req_payload = {
                    "features": [0.0] * 2381,
                    "request_id": f"req-mass-assign-{uuid.uuid4()}",
                    # Malicious extra fields intended for privilege escalation
                    "user_id": fake_victim_user_id,
                    "is_admin": True,
                    "role": "admin",
                    "decision": "pass",
                    "malware_score": 0.001,
                }
                resp = client.post(
                    "/v1/analyze/vector",
                    json=req_payload,
                    headers=analyst_headers,
                )
                assert resp.status_code == 200

                # Verify persisted job belongs to token-analyst, NOT fake_victim_user_id
                job = (
                    be15_db.query(AnalysisJob)
                    .filter_by(request_id=req_payload["request_id"])
                    .first()
                )
                assert job is not None
                expected_analyst_id = PREDEFINED_TOKENS["token-analyst"].user_id
                assert job.user_id == expected_analyst_id
                assert job.user_id != uuid.UUID(fake_victim_user_id)
        finally:
            app.dependency_overrides.clear()


# ===========================================================================
# 2. OBJECT-LEVEL AUTHORIZATION & IDOR/BOLA TESTS (GATES C & D)
# ===========================================================================


class TestObjectLevelAuthorizationAndIDOR:
    def test_cross_user_analysis_detail_idor_denied_403(self, be15_db: Session) -> None:
        """Analyst 2 cannot view Analyst 1's analysis detail (BOLA/IDOR protection)."""

        def override_db():
            yield be15_db

        app.dependency_overrides[get_db] = override_db
        try:
            with patch.object(settings, "api_auth_mode", "bearer"):
                a1_headers = {"Authorization": "Bearer token-analyst"}
                a2_headers = {"Authorization": "Bearer token-analyst-2"}

                # 1. Analyst 1 creates an analysis job
                req_id = f"req-idor-01-{uuid.uuid4()}"
                resp_create = client.post(
                    "/v1/analyze/vector",
                    json={"features": [0.0] * 2381, "request_id": req_id},
                    headers=a1_headers,
                )
                assert resp_create.status_code == 200

                # 2. Analyst 1 can view their own job
                resp_own = client.get(f"/v1/analysis/{req_id}", headers=a1_headers)
                assert resp_own.status_code == 200

                # 3. Analyst 2 attempts to read Analyst 1's job -> 403 XS_FORBIDDEN
                resp_cross = client.get(f"/v1/analysis/{req_id}", headers=a2_headers)
                assert resp_cross.status_code == 403
                assert resp_cross.json()["detail"]["code"] == "XS_FORBIDDEN"
                assert "another user" in resp_cross.json()["detail"]["message"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_cross_user_canonical_evidence_idor_denied_403(self, be15_db: Session) -> None:
        """Analyst 2 cannot retrieve canonical evidence for Analyst 1's job."""

        def override_db():
            yield be15_db

        app.dependency_overrides[get_db] = override_db
        try:
            with patch.object(settings, "api_auth_mode", "bearer"):
                a1_headers = {"Authorization": "Bearer token-analyst"}
                a2_headers = {"Authorization": "Bearer token-analyst-2"}

                # 1. Analyst 1 creates job
                req_id = f"req-idor-ev-{uuid.uuid4()}"
                resp_create = client.post(
                    "/v1/analyze/vector",
                    json={"features": [0.0] * 2381, "request_id": req_id},
                    headers=a1_headers,
                )
                assert resp_create.status_code == 200

                # 2. Analyst 1 can read own evidence
                resp_own_ev = client.get(f"/v1/analysis/{req_id}/evidence", headers=a1_headers)
                assert resp_own_ev.status_code == 200

                # 3. Analyst 2 attempts cross-user read of Analyst 1's evidence -> 403 XS_FORBIDDEN
                resp_cross_ev = client.get(f"/v1/analysis/{req_id}/evidence", headers=a2_headers)
                assert resp_cross_ev.status_code == 403
                assert resp_cross_ev.json()["detail"]["code"] == "XS_FORBIDDEN"
                assert "another user" in resp_cross_ev.json()["detail"]["message"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_analysis_history_listing_scoped_to_non_admin_owner(self, be15_db: Session) -> None:
        """When listing analysis jobs, non-admin users only see jobs they submitted."""

        def override_db():
            yield be15_db

        app.dependency_overrides[get_db] = override_db
        try:
            with patch.object(settings, "api_auth_mode", "bearer"):
                a1_headers = {"Authorization": "Bearer token-analyst"}
                a2_headers = {"Authorization": "Bearer token-analyst-2"}
                admin_headers = {"Authorization": "Bearer token-admin"}

                # Analyst 1 creates 2 jobs
                client.post(
                    "/v1/analyze/vector",
                    json={"features": [0.0] * 2381, "request_id": f"req-a1-1-{uuid.uuid4()}"},
                    headers=a1_headers,
                )
                client.post(
                    "/v1/analyze/vector",
                    json={"features": [0.0] * 2381, "request_id": f"req-a1-2-{uuid.uuid4()}"},
                    headers=a1_headers,
                )

                # Analyst 2 has submitted 0 jobs
                resp_list_a2 = client.get("/v1/analysis", headers=a2_headers)
                assert resp_list_a2.status_code == 200
                assert resp_list_a2.json()["total"] == 0

                # Analyst 1 sees exactly their 2 jobs
                resp_list_a1 = client.get("/v1/analysis", headers=a1_headers)
                assert resp_list_a1.status_code == 200
                assert resp_list_a1.json()["total"] == 2

                # Admin sees all jobs across all users
                resp_list_admin = client.get("/v1/analysis", headers=admin_headers)
                assert resp_list_admin.status_code == 200
                assert resp_list_admin.json()["total"] >= 2
        finally:
            app.dependency_overrides.clear()

    def test_admin_can_access_all_jobs_and_evidence(self, be15_db: Session) -> None:
        """Admin has full operational privileges across all users' jobs and evidence."""

        def override_db():
            yield be15_db

        app.dependency_overrides[get_db] = override_db
        try:
            with patch.object(settings, "api_auth_mode", "bearer"):
                a1_headers = {"Authorization": "Bearer token-analyst"}
                admin_headers = {"Authorization": "Bearer token-admin"}

                req_id = f"req-admin-access-{uuid.uuid4()}"
                client.post(
                    "/v1/analyze/vector",
                    json={"features": [0.0] * 2381, "request_id": req_id},
                    headers=a1_headers,
                )

                # Admin reads detail
                resp_det = client.get(f"/v1/analysis/{req_id}", headers=admin_headers)
                assert resp_det.status_code == 200

                # Admin reads evidence
                resp_ev = client.get(f"/v1/analysis/{req_id}/evidence", headers=admin_headers)
                assert resp_ev.status_code == 200
                assert resp_ev.json()["verified"] is True
        finally:
            app.dependency_overrides.clear()

    def test_evaluator_can_access_evidence_for_scoring(self, be15_db: Session) -> None:
        """Evaluator role has permission to read evidence for scientific evaluation scoring."""

        def override_db():
            yield be15_db

        app.dependency_overrides[get_db] = override_db
        try:
            with patch.object(settings, "api_auth_mode", "bearer"):
                a1_headers = {"Authorization": "Bearer token-analyst"}
                eval_headers = {"Authorization": "Bearer token-evaluator"}

                req_id = f"req-eval-evidence-{uuid.uuid4()}"
                client.post(
                    "/v1/analyze/vector",
                    json={"features": [0.0] * 2381, "request_id": req_id},
                    headers=a1_headers,
                )

                resp_ev = client.get(f"/v1/analysis/{req_id}/evidence", headers=eval_headers)
                assert resp_ev.status_code == 200
                assert resp_ev.json()["verified"] is True
        finally:
            app.dependency_overrides.clear()


# ===========================================================================
# 3. SECRET SCANNING & CREDENTIAL EXPOSURE TESTS (GATE E)
# ===========================================================================


class TestSecretScanningAndRedaction:
    def test_synthetic_private_key_detected_by_scanner(self) -> None:
        fake_key = (
            "-----BEGIN RSA PRIVATE KEY-----\n"  # synthetic
            "MIIEowIBAAKCAQEA0Yv+synthetic+key+for+testing+only\n"
            "-----END RSA PRIVATE KEY-----"
        )
        findings = scan_text_for_secrets(
            fake_key, file_path="test_mock.pem", ignore_synthetic=False
        )
        assert len(findings) == 1
        assert findings[0].secret_type == "PRIVATE_KEY"
        assert findings[0].severity == "P0_CRITICAL"

    def test_synthetic_aws_key_detected_by_scanner(self) -> None:
        fake_aws = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"  # synthetic
        findings = scan_text_for_secrets(fake_aws, ignore_synthetic=False)
        assert len(findings) == 1
        assert findings[0].secret_type == "AWS_KEY"

    def test_synthetic_db_password_in_url_detected_by_scanner(self) -> None:
        fake_url = (
            "XS_DATABASE_URL=mssql+pyodbc://sa:P@ssw0rd998877!@localhost:1433/db"  # synthetic
        )
        findings = scan_text_for_secrets(fake_url, ignore_synthetic=False)
        assert len(findings) == 1
        assert findings[0].secret_type == "DB_CONNECTION_PASSWORD"
        assert "***REDACTED***" in findings[0].masked_snippet

    def test_full_repository_secret_scan_passes_zero_critical(self) -> None:
        """Validates that real repository tree contains zero unwhitelisted critical secrets."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        findings = scan_directory_for_secrets(
            root=repo_root,
            exclude_dirs=(
                ".git",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                "node_modules",
                ".venv",
                "venv",
                ".gemini",
                "artifacts",
            ),
            ignore_synthetic=True,
        )
        critical = [f for f in findings if f.severity in {"P0_CRITICAL", "P1_HIGH"}]
        assert len(critical) == 0, f"Discovered exposed credentials: {critical}"

    def test_config_status_endpoint_exposes_no_secrets(self) -> None:
        """GET /v1/config/status must return non-secret metadata only."""
        resp = client.get("/v1/config/status")
        assert resp.status_code == 200
        data = resp.json()

        forbidden_keys = {"password", "secret", "token", "key", "credentials"}
        for k in data.keys():
            assert not any(f in k.lower() for f in forbidden_keys)

        # Database connection details must not leak credentials
        assert "database_url" not in data
        assert "password" not in str(data).lower()

    def test_redact_sensitive_text_and_dict(self) -> None:
        """Diagnostic redaction utilities redact credentials cleanly."""
        text = (
            "Database connection to mssql+pyodbc://sa:supersecretpassword123!@10.0.0.1 failed."
        )
        redacted_text = redact_sensitive_text(text)
        assert "supersecretpassword123!" not in redacted_text
        assert "[REDACTED]" in redacted_text

        payload = {
            "status": "error",
            "password": "RealSecretPassword123",  # synthetic
            "api_key": "sk-1234567890abcdef1234567890",  # synthetic
            "nested": {
                "token": "bearer-token-val",
                "safe_info": "ok",
            },
        }
        sanitized = redact_sensitive_dict(payload)
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["nested"]["token"] == "[REDACTED]"
        assert sanitized["nested"]["safe_info"] == "ok"


# ===========================================================================
# 4. BLIND CUSTODY & MANIFEST ACCESS DENIAL TESTS (GATE F)
# ===========================================================================


class TestBlindCustodyAndManifestAccessDenial:
    def test_defense_role_direct_file_access_denied_on_poison_manifest(self) -> None:
        """DEFENSE_DETECTOR role is forbidden from accessing manifest or poison files."""
        guard = BlindCustodyGuard(role=EvaluationRole.DEFENSE_DETECTOR)
        forbid_paths = [
            "artifacts/attack/manifest_e1.json",
            "data/poison_spec.json",
            "configs/ground_truth.yaml",
            "artifacts/blind_label_split.json",
        ]
        for p in forbid_paths:
            with pytest.raises(ManifestAccessDeniedError):
                guard.assert_path_allowed(p)

    def test_defense_role_path_traversal_attempt_denied(self, tmp_path: Path) -> None:
        """Path traversal sequences (../, %2e%2e, null byte) are strictly blocked."""
        with pytest.raises(PathTraversalAttemptError):
            assert_path_safe_from_traversal("../../../etc/passwd")

        with pytest.raises(PathTraversalAttemptError):
            assert_path_safe_from_traversal("data/../manifest.json")

        with pytest.raises(PathTraversalAttemptError):
            assert_path_safe_from_traversal("data/%2e%2e/poison.json")

        with pytest.raises(PathTraversalAttemptError):
            assert_path_safe_from_traversal("data/file\x00.json")

        # Escapes base directory check
        allowed_base = tmp_path / "allowed"
        allowed_base.mkdir()
        forbidden_target = tmp_path / "secret.txt"
        forbidden_target.write_text("secret")

        with pytest.raises(PathTraversalAttemptError):
            assert_path_safe_from_traversal(forbidden_target, base_dir=allowed_base)

    def test_defense_role_input_payload_leakage_denied(self) -> None:
        """Payload with blind labels or manifests raises BlindLabelLeakageError."""
        guard = BlindCustodyGuard(role=EvaluationRole.DEFENSE_DETECTOR)
        forbid_keys = [
            "blind_label",
            "ground_truth",
            "y_true",
            "poison_manifest",
            "trigger_manifest",
            "eval_label",
            "is_malware",
            "clean_model_score",
        ]
        for k in forbid_keys:
            with pytest.raises(BlindLabelLeakageError):
                guard.assert_defense_input_clean({k: 1})

            with pytest.raises(BlindLabelLeakageError):
                guard.assert_defense_input_clean({"nested": {"items": [{k: 0}]}})

    def test_defense_role_environment_variable_exposure_denied(self) -> None:
        """Exposing forbidden blind env vars raises ForbiddenEnvironmentExposureError."""
        guard = BlindCustodyGuard(role=EvaluationRole.DEFENSE_DETECTOR)
        forbid_env_vars = [
            "XS_BLIND_GROUND_TRUTH_PATH",
            "XS_POISON_MANIFEST_PATH",
            "XS_ATTACK_CUSTODY_KEY",
            "XS_BLIND_EVAL_LABELS",
        ]
        for var in forbid_env_vars:
            with pytest.raises(ForbiddenEnvironmentExposureError):
                guard.assert_environment_clean(env={var: "/path/to/manifest"})

    def test_application_schema_contains_zero_blind_ground_truth_tables(
        self, be15_db: Session
    ) -> None:
        """Validates that application database schema has no blind manifest tables."""
        assert verify_database_manifest_isolation(be15_db) is True

    def test_jev_ai_safe_context_rejects_blind_manifest_tokens(self) -> None:
        """Jev AI safe context rejects strings or payloads containing blind manifest tokens."""
        with pytest.raises(BlindLabelLeakageError):
            assert_jev_ai_safe_from_blind_data("Sample references poison_spec.json in notes")

        with pytest.raises(BlindLabelLeakageError):
            assert_jev_ai_safe_from_blind_data({"y_true": 1, "score": 0.9})

    def test_post_hoc_threshold_tuning_forbidden_during_evaluation(self) -> None:
        """BlindEvaluator detects and blocks post-hoc threshold manipulation."""
        pkg = BlindPredictionPackage.create(
            run_id="run-eval-01",
            experiment_code="E1",
            config_hash="c" * 64,
            model_hash="m" * 64,
            view_map_hash="v" * 64,
            detector_config_hash="d" * 64,
            threshold_id="D1_P95",
            threshold_value=0.75,
            seed=42,
            predictions=[
                BlindSamplePrediction(
                    sample_id="s1",
                    malware_score=0.8,
                    signals={"M1": 0.8},
                    fusion_score=0.8,
                    decision="ALERT",
                    latency_ms=1.5,
                )
            ],
        )

        truth = BlindGroundTruthManifest.create(
            manifest_id="truth-01",
            dataset_id="blind-eval-v3",
            sample_ids=["s1"],
            labels=[1],
            is_malware=[1],
        )

        evaluator = BlindEvaluator(role=EvaluationRole.EVALUATION_SCORING)

        # Tuning threshold away from locked 0.75 raises PostHocTuningForbiddenError
        with pytest.raises(PostHocTuningForbiddenError):
            evaluator.score_predictions(
                prediction_package=pkg,
                ground_truth=truth,
                expected_locked_threshold=0.50,  # Manipulated!
            )

    def test_evaluation_role_can_score_predictions_against_authorized_ground_truth(self) -> None:
        """Positive test: scoring succeeds when predictions are sealed and threshold matches."""
        pkg = BlindPredictionPackage.create(
            run_id="run-eval-02",
            experiment_code="E0",
            config_hash="c" * 64,
            model_hash="m" * 64,
            view_map_hash="v" * 64,
            detector_config_hash="d" * 64,
            threshold_id="D1_LOCKED",
            threshold_value=0.70,
            seed=42,
            predictions=[
                BlindSamplePrediction(
                    sample_id="s1",
                    malware_score=0.85,
                    signals={"M1": 0.85},
                    fusion_score=0.85,
                    decision="ALERT",
                    latency_ms=2.0,
                ),
                BlindSamplePrediction(
                    sample_id="s2",
                    malware_score=0.10,
                    signals={"M1": 0.10},
                    fusion_score=0.10,
                    decision="PASS",
                    latency_ms=1.8,
                ),
            ],
        )

        truth = BlindGroundTruthManifest.create(
            manifest_id="truth-02",
            dataset_id="blind-eval-v3",
            sample_ids=["s1", "s2"],
            labels=[1, 0],
            is_malware=[1, 0],
        )

        evaluator = BlindEvaluator(role=EvaluationRole.EVALUATION_SCORING)
        report = evaluator.score_predictions(
            prediction_package=pkg,
            ground_truth=truth,
            expected_locked_threshold=0.70,
        )

        assert report.run_id == "run-eval-02"
        assert report.locked_threshold == 0.70
        assert report.auroc == 1.0
        assert report.recall.recall == 1.0
        assert report.fpr.fpr == 0.0


# ===========================================================================
# 5. DATABASE SECURITY & IMMUTABILITY AUDIT TESTS (GATE G)
# ===========================================================================


class TestDatabaseSecurityAndAuditImmutability:
    def test_security_roles_sql_file_exists_and_contains_immutability_denials(self) -> None:
        sql_path = Path("database/schema/security_roles.sql")
        assert sql_path.exists(), "security_roles.sql must exist"
        sql_content = sql_path.read_text(encoding="utf-8")

        assert "xs_app_role" in sql_content
        assert "xs_readonly_role" in sql_content
        assert "xs_evaluation_role" in sql_content
        assert "DENY UPDATE, DELETE ON dbo.audit_events TO xs_app_role" in sql_content
        assert "DENY UPDATE, DELETE ON dbo.analysis_results TO xs_app_role" in sql_content
        assert (
            "DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::custody TO xs_app_role" in sql_content
        )

    def test_security_audit_event_recorded_cleanly(self, be15_db: Session) -> None:
        """Security audit event records mask tokens and persist to audit_events table."""
        fake_user = AuthUser(
            user_id=uuid.uuid4(),
            email="victim@xsentinel.local",
            roles=(Role.ANALYST.value,),
        )
        record_security_event(
            be15_db,
            event_type="auth.idor_blocked",
            user=fake_user,
            entity_type="analysis_job",
            entity_id=str(uuid.uuid4()),
            details={"requested_resource": "job_123", "token": "sensitive-bearer-token"},
            outcome="denied",
        )
        be15_db.commit()

        from x_sentinel.database.models import AuditEvent

        event = be15_db.query(AuditEvent).filter_by(event_type="security.auth.idor_blocked").first()
        assert event is not None
        assert event.user_id == fake_user.user_id
        # Verify token was redacted
        assert event.payload["token"] == "[REDACTED]"
        assert event.payload["outcome"] == "denied"
