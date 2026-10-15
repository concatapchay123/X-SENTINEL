# ruff: noqa: B008
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from x_sentinel.config import settings
from x_sentinel.security.policy import (
    Permission,
    get_permissions_for_roles,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from x_sentinel.database.models import AnalysisJob


class Role(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    EVALUATOR = "evaluator"
    OPERATOR = "operator"


class ObjectAccessDeniedError(HTTPException):
    """Raised when an authenticated principal attempts cross-user access
    to an unauthorized object.
    """

    def __init__(
        self,
        message: str = "Access denied: resource belongs to another user",
        code: str = "XS_FORBIDDEN",
    ) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": code, "message": message},
        )


@dataclass(frozen=True)
class AuthUser:
    """Authenticated user context with assigned roles and derived permissions."""

    user_id: uuid.UUID
    email: str
    roles: tuple[str, ...] = field(default_factory=tuple)
    is_active: bool = True

    def has_role(self, *required_roles: str) -> bool:
        if not required_roles:
            return True
        return any(r in self.roles for r in required_roles)

    def has_permission(self, *required_permissions: Permission | str) -> bool:
        if not required_permissions:
            return True
        user_perms = get_permissions_for_roles(self.roles)
        for p in required_permissions:
            perm_enum = Permission(p) if isinstance(p, str) else p
            if perm_enum in user_perms:
                return True
        return False

    @property
    def permissions(self) -> frozenset[Permission]:
        return get_permissions_for_roles(self.roles)


# Predefined tokens for testing and development environments
PREDEFINED_TOKENS: dict[str, AuthUser] = {
    "token-admin": AuthUser(
        user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        email="admin@xsentinel.local",
        roles=(Role.ADMIN.value, Role.ANALYST.value, Role.OPERATOR.value),
    ),
    "token-analyst": AuthUser(
        user_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        email="analyst@xsentinel.local",
        roles=(Role.ANALYST.value, Role.OPERATOR.value),
    ),
    "token-evaluator": AuthUser(
        user_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        email="evaluator@xsentinel.local",
        roles=(Role.EVALUATOR.value,),
    ),
    "token-operator": AuthUser(
        user_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        email="operator@xsentinel.local",
        roles=(Role.OPERATOR.value,),
    ),
    "token-analyst-2": AuthUser(
        user_id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        email="analyst2@xsentinel.local",
        roles=(Role.ANALYST.value, Role.OPERATOR.value),
    ),
    "token-inactive": AuthUser(
        user_id=uuid.UUID("66666666-6666-6666-6666-666666666666"),
        email="inactive@xsentinel.local",
        roles=(Role.ADMIN.value, Role.ANALYST.value),
        is_active=False,
    ),
}

# Default unauthenticated identity when auth is disabled
ANONYMOUS_USER = AuthUser(
    user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
    email="anonymous@xsentinel.local",
    roles=(Role.ADMIN.value, Role.ANALYST.value, Role.OPERATOR.value, Role.EVALUATOR.value),
)

http_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Security(http_bearer_scheme),
) -> AuthUser | None:
    """Returns the authenticated user, or ANONYMOUS_USER if auth is disabled.

    When settings.api_auth_mode == 'none', returns ANONYMOUS_USER without requiring credentials.
    When auth is enabled:
      - If credentials are missing, returns None (optional auth).
      - If credentials are valid, returns the corresponding AuthUser.
      - If user is inactive, raises HTTP 403 XS_FORBIDDEN.
      - If credentials are invalid, raises HTTP 401 XS_INVALID_CREDENTIALS.
    """
    if settings.api_auth_mode == "none":
        return ANONYMOUS_USER

    if credentials is None:
        return None

    token = credentials.credentials.strip()
    if token in PREDEFINED_TOKENS:
        user = PREDEFINED_TOKENS[token]
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "XS_FORBIDDEN",
                    "message": "Authenticated user account is inactive",
                },
            )
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "XS_INVALID_CREDENTIALS",
            "message": "Invalid or expired authentication credentials",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(http_bearer_scheme),
) -> AuthUser:
    """Enforces authentication according to settings.api_auth_mode.

    When settings.api_auth_mode == 'none', returns ANONYMOUS_USER.
    When settings.api_auth_mode != 'none', requires valid credentials:
      - Missing credentials -> 401 XS_UNAUTHENTICATED
      - Invalid credentials -> 401 XS_INVALID_CREDENTIALS
      - Inactive account -> 403 XS_FORBIDDEN
    """
    if settings.api_auth_mode == "none":
        return ANONYMOUS_USER

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "XS_UNAUTHENTICATED", "message": "Missing authentication credentials"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    if token in PREDEFINED_TOKENS:
        user = PREDEFINED_TOKENS[token]
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "XS_FORBIDDEN",
                    "message": "Authenticated user account is inactive",
                },
            )
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "XS_INVALID_CREDENTIALS",
            "message": "Invalid or expired authentication credentials",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_roles(*allowed_roles: str):
    """Factory creating a FastAPI dependency that verifies the user has one of allowed_roles."""

    def role_checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if settings.api_auth_mode == "none":
            return user

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "XS_FORBIDDEN",
                    "message": "Authenticated user account is inactive",
                },
            )

        if not user.has_role(*allowed_roles):
            msg = (
                f"Action requires one of roles: {list(allowed_roles)}; user has {list(user.roles)}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "XS_FORBIDDEN",
                    "message": msg,
                },
            )
        return user

    return role_checker


def require_permissions(*required_permissions: Permission | str):
    """Factory creating a FastAPI dependency verifying at least one permission."""

    def permission_checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if settings.api_auth_mode == "none":
            return user

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "XS_FORBIDDEN",
                    "message": "Authenticated user account is inactive",
                },
            )

        if not user.has_permission(*required_permissions):
            req_names = [
                p.value if isinstance(p, Permission) else str(p) for p in required_permissions
            ]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "XS_FORBIDDEN",
                    "message": f"Action requires permission from {req_names}",
                },
            )
        return user

    return permission_checker


def is_admin(user: AuthUser | None) -> bool:
    """Checks whether principal is admin or running in unauthenticated development mode."""
    if settings.api_auth_mode == "none" or user is None:
        return True
    if user.user_id == ANONYMOUS_USER.user_id:
        return True
    return user.has_role(Role.ADMIN.value)


def assert_job_ownership(
    job: AnalysisJob,
    user: AuthUser | None,
    *,
    allow_evaluator: bool = False,
    resource_label: str = "analysis record",
) -> None:
    """Verifies object-level ownership (BOLA/IDOR prevention).

    Admins can access any job. Evaluators can access if allow_evaluator is True.
    Non-admin users can only access jobs they own.
    """
    if is_admin(user):
        return
    if allow_evaluator and user is not None and user.has_role(Role.EVALUATOR.value):
        return
    if job.user_id is not None and user is not None and job.user_id != user.user_id:
        raise ObjectAccessDeniedError(
            message=f"Access denied: {resource_label} belongs to another user",
            code="XS_FORBIDDEN",
        )


def ensure_persisted_user(session: Session, user: AuthUser | None) -> uuid.UUID | None:
    """Ensures an authenticated non-anonymous user exists in the users table and returns UUID."""
    if user is None or settings.api_auth_mode == "none" or user.user_id == ANONYMOUS_USER.user_id:
        return None

    from x_sentinel.database.models import User

    existing = session.get(User, user.user_id)
    if existing is None:
        primary_role = (
            Role.ADMIN.value
            if Role.ADMIN.value in user.roles
            else (user.roles[0] if user.roles else Role.ANALYST.value)
        )
        new_user = User(
            id=user.user_id,
            email=user.email,
            normalized_email=user.email.strip().lower(),
            display_name=primary_role,
            is_active=user.is_active,
        )
        session.add(new_user)
        session.flush()
    return user.user_id
