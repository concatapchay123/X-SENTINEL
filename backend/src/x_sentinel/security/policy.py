from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum


class SecurityClassification(StrEnum):
    """Data security classification tiers for X-SENTINEL V3."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    BLIND_CUSTODY = "BLIND_CUSTODY"


class Permission(StrEnum):
    """Canonical permission identifiers adhering to 19_PERMISSION_MATRIX.md."""

    ANALYSIS_SUBMIT = "analysis:submit"
    ANALYSIS_READ = "analysis:read"
    ANALYSIS_READ_ALL = "analysis:read_all"
    EVIDENCE_READ = "evidence:read"
    ALERTS_READ = "alerts:read"
    ALERTS_MUTATE = "alerts:mutate"
    AI_INVOKE = "ai:invoke"
    AI_READ = "ai:read"
    AI_FEEDBACK = "ai:feedback"
    EVALUATION_SCORE = "evaluation:score"
    CONFIG_WRITE = "config:write"
    ADMIN_OPS = "admin:ops"


# Canonical Role -> Permissions mapping based on docs/baseline/19_PERMISSION_MATRIX.md
ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "admin": frozenset(Permission),
    "analyst": frozenset(
        {
            Permission.ANALYSIS_SUBMIT,
            Permission.ANALYSIS_READ,
            Permission.EVIDENCE_READ,
            Permission.ALERTS_READ,
            Permission.ALERTS_MUTATE,
            Permission.AI_INVOKE,
            Permission.AI_READ,
            Permission.AI_FEEDBACK,
        }
    ),
    "evaluator": frozenset(
        {
            Permission.ANALYSIS_READ,
            Permission.EVIDENCE_READ,
            Permission.ALERTS_READ,
            Permission.EVALUATION_SCORE,
        }
    ),
    "operator": frozenset(
        {
            Permission.ANALYSIS_SUBMIT,
            Permission.ANALYSIS_READ,
            Permission.ALERTS_READ,
        }
    ),
}


def has_permission(roles: Sequence[str], permission: Permission | str) -> bool:
    """Evaluates whether any assigned role possesses the requested permission under default-deny."""
    perm = Permission(permission) if isinstance(permission, str) else permission
    for r in roles:
        role_key = r.lower().strip()
        perms = ROLE_PERMISSIONS.get(role_key, frozenset())
        if perm in perms:
            return True
    return False


def get_permissions_for_roles(roles: Sequence[str]) -> frozenset[Permission]:
    """Returns the union of all permissions granted across assigned roles."""
    aggregated: set[Permission] = set()
    for r in roles:
        role_key = r.lower().strip()
        aggregated.update(ROLE_PERMISSIONS.get(role_key, frozenset()))
    return frozenset(aggregated)


def assert_safe_runtime(*, demo_mode: bool, auth_mode: str, bind_host: str) -> None:
    """Enforces server runtime security invariants."""
    if auth_mode == "none" and bind_host not in {"127.0.0.1", "localhost", "0.0.0.0"}:
        raise RuntimeError(
            "unauthenticated network exposure requires an approved security decision"
        )
    if not isinstance(demo_mode, bool):
        raise RuntimeError("demo mode must be explicit")
