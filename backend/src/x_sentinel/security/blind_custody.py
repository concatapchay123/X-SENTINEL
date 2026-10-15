from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from x_sentinel.evaluation.blind import (
    FORBIDDEN_DEFENSE_ENV_VARS,
    FORBIDDEN_DEFENSE_KEYS,
    FORBIDDEN_FILENAME_TOKENS,
    BlindCustodyGuard,
    BlindCustodyIntegrityError,
    BlindLabelLeakageError,
    BlindProtocolViolationError,
    BlindRolePermissionError,
    EvaluationRole,
    ForbiddenEnvironmentExposureError,
    ManifestAccessDeniedError,
    PostHocTuningForbiddenError,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class PathTraversalAttemptError(PermissionError):
    """Raised when a file path attempts directory traversal outside designated boundaries."""


def assert_path_safe_from_traversal(
    target_path: Path | str,
    base_dir: Path | str | None = None,
) -> Path:
    """Validates that a path is safe against directory traversal and null-byte injection.

    Args:
        target_path: Target path string or Path object.
        base_dir: Optional root directory that target_path must strictly reside within.

    Returns:
        Resolved safe Path object.

    Raises:
        PathTraversalAttemptError: If traversal sequence or out-of-boundary access is detected.
    """
    raw_str = str(target_path)
    if "\x00" in raw_str:
        raise PathTraversalAttemptError("Path contains null byte sequence.")

    # Check for encoded or relative path traversal sequences
    if ".." in raw_str.replace("\\", "/").split("/"):
        raise PathTraversalAttemptError(
            f"Path traversal sequence ('..') detected in path: '{raw_str}'"
        )
    if "%2e%2e" in raw_str.lower() or "%2f" in raw_str.lower():
        raise PathTraversalAttemptError(
            f"Encoded path traversal sequence detected in path: '{raw_str}'"
        )

    resolved = Path(target_path).resolve()

    if base_dir is not None:
        resolved_base = Path(base_dir).resolve()
        if resolved != resolved_base and resolved_base not in resolved.parents:
            raise PathTraversalAttemptError(
                f"Path '{resolved}' escapes allowed base directory '{resolved_base}'"
            )

    return resolved


def assert_defense_cannot_access_manifest(
    target_path: Path | str,
    role: EvaluationRole | str = EvaluationRole.DEFENSE_DETECTOR,
    restricted_custody_paths: Sequence[Path | str] | None = None,
) -> None:
    """Enforces that DEFENSE_DETECTOR cannot read poisoning manifests or hidden ground-truth.

    Combines path traversal normalization with BlindCustodyGuard enforcement.
    """
    eval_role = EvaluationRole(role) if isinstance(role, str) else role
    safe_path = assert_path_safe_from_traversal(target_path)
    guard = BlindCustodyGuard(role=eval_role, restricted_custody_paths=restricted_custody_paths)
    guard.assert_path_allowed(safe_path)


def verify_database_manifest_isolation(session: Session) -> bool:
    """Verifies that MSSQL application schema contains zero blind ground-truth tables.

    Fulfills invariant: 'Blind ground-truth/manifest data is intentionally absent
    from this application schema.'
    """
    from x_sentinel.database.base import Base

    app_table_names = {t.lower() for t in Base.metadata.tables.keys()}
    forbidden_table_tokens = ("manifest", "ground_truth", "blind_label", "poison")

    for t_name in app_table_names:
        for token in forbidden_table_tokens:
            if token in t_name:
                msg = f"Forbidden blind custody table '{t_name}' in schema metadata!"
                raise BlindProtocolViolationError(msg)
    return True


def verify_process_environment_isolation(
    role: EvaluationRole = EvaluationRole.DEFENSE_DETECTOR,
    env: dict[str, str] | None = None,
) -> bool:
    """Verifies that the defense process environment has zero blind custody env vars exposed."""
    guard = BlindCustodyGuard(role=role)
    guard.assert_environment_clean(env=env)
    return True


def assert_jev_ai_safe_from_blind_data(context_payload: Mapping[str, Any] | str) -> None:
    """Verifies that no blind manifest keys or tokens leak into Jev AI safe context."""
    if isinstance(context_payload, str):
        lower = context_payload.lower()
        for token in FORBIDDEN_FILENAME_TOKENS:
            if token in lower:
                raise BlindLabelLeakageError(
                    f"Forbidden blind token '{token}' discovered in Jev AI context string."
                )
    elif isinstance(context_payload, Mapping):
        guard = BlindCustodyGuard(role=EvaluationRole.DEFENSE_DETECTOR)
        guard.assert_defense_input_clean(context_payload)


__all__ = [
    "FORBIDDEN_DEFENSE_ENV_VARS",
    "FORBIDDEN_DEFENSE_KEYS",
    "FORBIDDEN_FILENAME_TOKENS",
    "BlindCustodyGuard",
    "BlindCustodyIntegrityError",
    "BlindLabelLeakageError",
    "BlindProtocolViolationError",
    "BlindRolePermissionError",
    "EvaluationRole",
    "ForbiddenEnvironmentExposureError",
    "ManifestAccessDeniedError",
    "PathTraversalAttemptError",
    "PostHocTuningForbiddenError",
    "assert_defense_cannot_access_manifest",
    "assert_jev_ai_safe_from_blind_data",
    "assert_path_safe_from_traversal",
    "verify_database_manifest_isolation",
    "verify_process_environment_isolation",
]
