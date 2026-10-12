from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from x_sentinel.config import settings


class Role(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    EVALUATOR = "evaluator"
    OPERATOR = "operator"


@dataclass(frozen=True)
class AuthUser:
    """Authenticated user context with assigned roles."""

    user_id: uuid.UUID
    email: str
    roles: tuple[str, ...] = field(default_factory=tuple)
    is_active: bool = True

    def has_role(self, *required_roles: str) -> bool:
        if not required_roles:
            return True
        return any(r in self.roles for r in required_roles)


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
      - If credentials are invalid, raises HTTP 401 XS_INVALID_CREDENTIALS.
    """
    if settings.api_auth_mode == "none":
        return ANONYMOUS_USER

    if credentials is None:
        return None

    token = credentials.credentials.strip()
    if token in PREDEFINED_TOKENS:
        return PREDEFINED_TOKENS[token]

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
        return PREDEFINED_TOKENS[token]

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

        if not user.has_role(*allowed_roles):
            msg = (
                f"Action requires one of roles: {list(allowed_roles)}; "
                f"user has {list(user.roles)}"
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
