from __future__ import annotations

import hashlib
from pathlib import Path
import pytest

from x_sentinel.audit.artifacts import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactRecord,
    ArtifactSecurityError,
    compute_file_sha256,
    create_artifact_record_from_file,
    validate_artifact_path,
    verify_artifact_file,
)


class TestArtifactContracts:
    """Verifies artifact identity, checksum verification, and directory traversal safety."""

    def test_artifact_record_validation(self) -> None:
        rec = ArtifactRecord(
            kind="model",
            uri="models/model.lgb",
            sha256="a" * 64,
            size_bytes=1024,
            content_type="application/octet-stream",
            metadata_json={"version": "1.0"},
        )
        assert rec.kind == "model"
        assert rec.sha256 == "a" * 64
        assert rec.size_bytes == 1024
        assert rec.to_dict()["kind"] == "model"

    def test_artifact_record_invalid_kind_rejected(self) -> None:
        with pytest.raises(ValueError, match="Artifact kind must be one of"):
            ArtifactRecord(
                kind="unauthorized_kind",
                uri="models/model.lgb",
                sha256="a" * 64,
            )

    def test_artifact_record_invalid_sha256_rejected(self) -> None:
        with pytest.raises(ValueError, match="Artifact sha256 must be a 64-character hex string"):
            ArtifactRecord(
                kind="model",
                uri="models/model.lgb",
                sha256="short_hash",
            )

        with pytest.raises(ValueError, match="Artifact sha256 must be valid hexadecimal"):
            ArtifactRecord(
                kind="model",
                uri="models/model.lgb",
                sha256="z" * 64,
            )

    def test_compute_and_verify_file_sha256(self, tmp_path: Path) -> None:
        sample_file = tmp_path / "test_artifact.bin"
        sample_content = b"X-SENTINEL V3 CANONICAL ARTIFACT CONTENT"
        sample_file.write_bytes(sample_content)

        expected_hash = hashlib.sha256(sample_content).hexdigest()
        computed_hash = compute_file_sha256(sample_file)

        assert computed_hash == expected_hash
        assert verify_artifact_file(sample_file, expected_hash) is True

    def test_verify_file_sha256_detects_tampering(self, tmp_path: Path) -> None:
        sample_file = tmp_path / "tampered_artifact.bin"
        sample_file.write_bytes(b"ORIGINAL CONTENT")
        expected_hash = hashlib.sha256(b"ORIGINAL CONTENT").hexdigest()

        # Tamper content
        sample_file.write_bytes(b"MODIFIED TAMPERED CONTENT")

        with pytest.raises(ArtifactIntegrityError, match="Artifact checksum mismatch"):
            verify_artifact_file(sample_file, expected_hash)

    def test_verify_file_not_found(self, tmp_path: Path) -> None:
        non_existent = tmp_path / "missing.bin"
        with pytest.raises(ArtifactNotFoundError, match="File not found"):
            verify_artifact_file(non_existent, "0" * 64)

    def test_create_artifact_record_from_file(self, tmp_path: Path) -> None:
        artifact_file = tmp_path / "calibration.json"
        content = b'{"threshold": 0.50}'
        artifact_file.write_bytes(content)

        rec = create_artifact_record_from_file(
            file_path=artifact_file,
            kind="calibration",
            content_type="application/json",
            metadata={"source": "d1"},
        )
        assert rec.kind == "calibration"
        assert rec.size_bytes == len(content)
        assert rec.sha256 == hashlib.sha256(content).hexdigest()
        assert rec.metadata_json == {"source": "d1"}

    def test_validate_artifact_path_traversal_prevention(self, tmp_path: Path) -> None:
        safe_dir = tmp_path / "allowed_artifacts"
        safe_dir.mkdir()
        safe_file = safe_dir / "safe.json"
        safe_file.write_text("{}")

        # Safe access works
        validated = validate_artifact_path(safe_file, allowed_base_dir=safe_dir)
        assert validated == safe_file.resolve()

        # Directory traversal attempt
        outside_file = tmp_path / "outside.secret"
        outside_file.write_text("SECRET")

        traversal_path = safe_dir / ".." / "outside.secret"
        with pytest.raises(ArtifactSecurityError, match="attempts traversal outside allowed base directory"):
            validate_artifact_path(traversal_path, allowed_base_dir=safe_dir)
