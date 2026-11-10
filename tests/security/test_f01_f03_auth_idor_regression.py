from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from x_sentinel.config import Settings
from x_sentinel.database.models import Alert, AnalysisJob, AuditEvent, Base, User
from x_sentinel.security.auth import (
    ANONYMOUS_USER,
    AuthUser,
    ObjectAccessDeniedError,
    Role,
    get_current_user,
    is_admin,
)
from x_sentinel.services.alert_service import AlertService


def test_production_forbids_auth_mode_none():
    """F01: Settings must raise ValueError if env='production' and api_auth_mode='none'."""
    with pytest.raises(ValueError, match="Production environment strictly forbids api_auth_mode='none'"):
        Settings(env="production", api_auth_mode="none")


def test_production_forbids_allow_predefined_tokens():
    """F01: Settings must raise ValueError if env='production' and allow_predefined_tokens=True."""
    with pytest.raises(ValueError, match="strictly forbids allow_predefined_tokens=True"):
        Settings(env="production", api_auth_mode="bearer", allow_predefined_tokens=True)


def test_is_admin_default_deny():
    """F01: is_admin must return False for None, Anonymous, and non-admin users."""
    assert is_admin(None) is False
    assert is_admin(ANONYMOUS_USER) is False

    analyst = AuthUser(
        user_id=uuid.uuid4(),
        email="analyst@xsentinel.local",
        roles=(Role.ANALYST.value,),
    )
    assert is_admin(analyst) is False

    admin = AuthUser(
        user_id=uuid.uuid4(),
        email="admin@xsentinel.local",
        roles=(Role.ADMIN.value,),
    )
    assert is_admin(admin) is True


def test_anonymous_user_has_zero_roles():
    """F01: ANONYMOUS_USER must not carry admin or analyst privileges by default."""
    assert ANONYMOUS_USER.roles == ()
    assert not ANONYMOUS_USER.has_role(Role.ADMIN.value)
    assert not ANONYMOUS_USER.has_role(Role.ANALYST.value)


def test_production_rejects_predefined_tokens(monkeypatch):
    """F01: Production mode must reject hardcoded demo tokens with 401 XS_INVALID_CREDENTIALS."""
    from x_sentinel.config import settings

    monkeypatch.setattr(settings, "env", "production")
    monkeypatch.setattr(settings, "api_auth_mode", "bearer")
    monkeypatch.setattr(settings, "allow_predefined_tokens", False)

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token-admin")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds)

    assert exc_info.value.status_code == 401
    assert isinstance(exc_info.value.detail, dict)
    assert exc_info.value.detail["code"] == "XS_INVALID_CREDENTIALS"


def test_alert_ownership_idor_prevented():
    """F03: Analyst B must be strictly forbidden from listing, viewing, or mutating Analyst A's alert."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for col in Base.metadata.tables["audit_events"].columns:
        if col.name == "id":
            from sqlalchemy import Integer
            col.type = Integer()

    for table in (User.__table__, AnalysisJob.__table__, Alert.__table__, AuditEvent.__table__):
        for col in cast(Any, table.columns):
            if col.server_default is not None and hasattr(col.server_default, "arg"):
                text_str = str(col.server_default.arg)
                if "N'" in text_str:
                    col.server_default.arg.text = text_str.replace("N'", "'")

    cast(Any, User.__table__).create(engine)
    cast(Any, AnalysisJob.__table__).create(engine)
    cast(Any, Alert.__table__).create(engine)
    cast(Any, AuditEvent.__table__).create(engine)

    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    analyst_a = AuthUser(user_id=user_a_id, email="a@test.com", roles=(Role.ANALYST.value,))
    analyst_b = AuthUser(user_id=user_b_id, email="b@test.com", roles=(Role.ANALYST.value,))
    admin_user = AuthUser(user_id=admin_id, email="admin@test.com", roles=(Role.ADMIN.value,))

    with Session(engine) as session:
        # Create Job owned by Analyst A
        job_a = AnalysisJob(
            id=uuid.uuid4(),
            request_id="req-test-owner-a",
            user_id=user_a_id,
            status="completed",
            input_mode="vector",
            input_sha256="a" * 64,
            created_at=datetime.now(UTC),
        )
        session.add(job_a)

        # Create Alert associated with Job A
        alert_a = Alert(
            id=uuid.uuid4(),
            analysis_job_id=job_a.id,
            severity="high",
            status="open",
            reason="High suspicion score",
            created_at=datetime.now(UTC),
        )
        session.add(alert_a)
        session.commit()

        alert_svc = AlertService()

        # 1. Analyst B queries alert list filtered by job_a -> returns 0 items
        items_b, total_b = alert_svc.list_alerts(
            session=session,
            analysis_job_id=str(job_a.id),
            user=analyst_b,
        )
        assert len(items_b) == 0
        assert total_b == 0

        # Analyst A queries alert list -> returns 1 item
        items_a, total_a = alert_svc.list_alerts(
            session=session,
            analysis_job_id=str(job_a.id),
            user=analyst_a,
        )
        assert len(items_a) == 1
        assert total_a == 1

        # 2. Analyst B attempts get_alert for alert_a -> raises 403 XS_FORBIDDEN
        with pytest.raises(ObjectAccessDeniedError) as exc_get:
            alert_svc.get_alert(session=session, alert_id=alert_a.id, user=analyst_b)
        assert exc_get.value.status_code == 403
        assert isinstance(exc_get.value.detail, dict)
        assert exc_get.value.detail["code"] == "XS_FORBIDDEN"

        # 3. Analyst B attempts update_alert_status for alert_a -> raises 403 XS_FORBIDDEN
        with pytest.raises(ObjectAccessDeniedError) as exc_patch:
            alert_svc.update_alert_status(
                session=session,
                alert_id=alert_a.id,
                new_status="acknowledged",
                user=analyst_b,
            )
        assert exc_patch.value.status_code == 403
        assert isinstance(exc_patch.value.detail, dict)
        assert exc_patch.value.detail["code"] == "XS_FORBIDDEN"

        # 4. Admin user can successfully view and update alert_a
        summary = alert_svc.get_alert(session=session, alert_id=alert_a.id, user=admin_user)
        assert summary is not None
        assert summary.id == str(alert_a.id)

        updated = alert_svc.update_alert_status(
            session=session,
            alert_id=alert_a.id,
            new_status="acknowledged",
            user=admin_user,
        )
        assert updated.status == "acknowledged"
