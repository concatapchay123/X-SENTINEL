from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any
import uuid


class ArtifactError(Exception):
    """Base exception for artifact operations."""


class ArtifactIntegrityError(ArtifactError):
    """Raised when an artifact checksum does not match expected value."""


class ArtifactNotFoundError(ArtifactError):
    """Raised when an artifact file or reference cannot be found."""


class ArtifactSecurityError(ArtifactError):
    """Raised when an artifact path violates safety boundaries (e.g. path traversal)."""


ALLOWED_ARTIFACT_KINDS = frozenset(
    {"model", "config", "calibration", "evidence", "dataset", "report", "vector"}
)


@dataclass(frozen=True)
class ArtifactRecord:
    """Canonical artifact identity record matching the database artifacts schema."""

    kind: str
    uri: str
    sha256: str
    analysis_job_id: uuid.UUID | str | None = None
    id: uuid.UUID | str = field(default_factory=uuid.uuid4)
    content_type: str | None = None
    size_bytes: int | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.kind not in ALLOWED_ARTIFACT_KINDS:
            raise ValueError(
                f"Artifact kind must be one of {sorted(ALLOWED_ARTIFACT_KINDS)}, got {self.kind!r}"
            )
        if not isinstance(self.uri, str) or not self.uri.strip():
            raise ValueError("Artifact uri must be a non-empty string.")
        if not isinstance(self.sha256, str) or len(self.sha256) != 64:
            raise ValueError(f"Artifact sha256 must be a 64-character hex string, got {self.sha256!r}")
        try:
            int(self.sha256, 16)
        except ValueError as exc:
            raise ValueError(f"Artifact sha256 must be valid hexadecimal: {exc}") from exc

        if self.size_bytes is not None and self.size_bytes < 0:
            raise ValueError("Artifact size_bytes cannot be negative.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "analysis_job_id": str(self.analysis_job_id) if self.analysis_job_id else None,
            "kind": self.kind,
            "uri": self.uri,
            "sha256": self.sha256,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "metadata_json": dict(self.metadata_json),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def compute_file_sha256(path: Path | str, chunk_size: int = 65536) -> str:
    """Computes SHA-256 checksum of a file in streaming binary chunks."""
    target_path = Path(path)
    if not target_path.exists() or not target_path.is_file():
        raise ArtifactNotFoundError(f"File not found: {target_path}")

    hasher = hashlib.sha256()
    with target_path.open("rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_artifact_file(path: Path | str, expected_sha256: str) -> bool:
    """Verifies that a local file matches the expected SHA-256 checksum."""
    clean_expected = expected_sha256.strip().lower()
    if len(clean_expected) != 64:
        raise ValueError(f"expected_sha256 must be 64 hex characters, got {expected_sha256!r}")

    computed = compute_file_sha256(path)
    if computed != clean_expected:
        raise ArtifactIntegrityError(
            f"Artifact checksum mismatch for {path}: computed {computed}, expected {clean_expected}"
        )
    return True


def validate_artifact_path(
    path: Path | str,
    allowed_base_dir: Path | str | None = None,
) -> Path:
    """Ensures the artifact path is safe against directory traversal."""
    resolved_path = Path(path).resolve()
    if allowed_base_dir is not None:
        base_dir = Path(allowed_base_dir).resolve()
        try:
            resolved_path.relative_to(base_dir)
        except ValueError as exc:
            raise ArtifactSecurityError(
                f"Artifact path {path} attempts traversal outside allowed base directory {base_dir}"
            ) from exc
    return resolved_path


def create_artifact_record_from_file(
    file_path: Path | str,
    kind: str,
    analysis_job_id: uuid.UUID | str | None = None,
    content_type: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ArtifactRecord:
    """Creates a validated ArtifactRecord directly from an existing file."""
    path = Path(file_path)
    sha256 = compute_file_sha256(path)
    size_bytes = path.stat().st_size
    return ArtifactRecord(
        kind=kind,
        uri=str(path.as_posix()),
        sha256=sha256,
        analysis_job_id=analysis_job_id,
        content_type=content_type,
        size_bytes=size_bytes,
        metadata_json=metadata or {},
        created_at=datetime.now(timezone.utc),
    )
