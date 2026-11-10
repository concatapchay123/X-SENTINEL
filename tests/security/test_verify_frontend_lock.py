"""Unit and adversarial integration tests for Gate G01 Cryptographic Frontend Lock.

Validates that scripts/verify_frontend_lock.py correctly and reliably:
1. Passes on clean repository tree (exit 0).
2. Detects same-size byte modifications (SHA-256 mismatch, size matched).
3. Detects size changes (size mismatch).
4. Detects deleted / missing locked files.
5. Detects extraneous / unauthorized files in locked directories.
6. Detects forbidden docs/frontend/ directory containing files.
7. Detects rogue PLAN-FE-* and TASK-FE-* files outside docs/plans/frontend/.
8. Handles corrupted / missing manifest files gracefully.
9. Guarantees zero permanent modifications to locked repository files.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.verify_frontend_lock import (
    compute_sha256,
    execute_verification,
    load_manifest,
    verify_directory_exclusivity,
    verify_locked_files,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = PROJECT_ROOT / "docs" / "governance" / "FRONTEND_LOCK_MANIFEST.json"


def test_positive_clean_tree_direct_execution():
    """Verify that execute_verification succeeds with 0 errors on clean repository."""
    assert MANIFEST_PATH.is_file(), f"Manifest file missing: {MANIFEST_PATH}"
    report = execute_verification(PROJECT_ROOT, MANIFEST_PATH)

    assert report["is_valid"] is True
    assert report["status"] == "PASS"
    assert report["total_locked_files"] == 31
    assert report["verified_count"] == 31
    assert report["missing_count"] == 0
    assert report["hash_mismatch_count"] == 0
    assert report["size_mismatch_count"] == 0
    assert report["extraneous_count"] == 0
    assert report["forbidden_dir_count"] == 0


def test_positive_clean_tree_cli():
    """Verify scripts/verify_frontend_lock.py CLI exits with code 0 on clean tree."""
    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "verify_frontend_lock.py")]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)

    assert proc.returncode == 0, f"Script failed with output:\n{proc.stdout}\n{proc.stderr}"
    assert "VERDICT: PASS" in proc.stdout
    assert "Verified Intact    : 31" in proc.stdout


def test_positive_clean_tree_cli_json():
    """Verify CLI --json outputs structured report with status PASS."""
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "verify_frontend_lock.py"),
        "--json",
    ]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)

    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["status"] == "PASS"
    assert data["is_valid"] is True
    assert data["total_locked_files"] == 31
    assert data["verified_count"] == 31


def test_adversarial_hash_mismatch_same_byte_size():
    """Adversarial Test: 1 byte flipped (size unchanged) triggers HASH MISMATCH with exit 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_p = Path(tmpdir)
        mock_root = tmp_p / "repo"
        mock_root.mkdir()

        # Create mock file with known content
        file_rel = "frontend/app.py"
        target = mock_root / file_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        content = b"original content for testing exact byte match"
        target.write_bytes(content)

        # Flipped 1 byte: same length, different hash
        tampered_content = b"xriginal content for testing exact byte match"
        assert len(tampered_content) == len(content)
        target.write_bytes(tampered_content)

        mock_manifest = {
            "locked_files": [
                {
                    "relative_path": file_rel,
                    "sha256": compute_sha256(Path(__file__)),  # deliberately different hash
                    "size_bytes": len(tampered_content),
                }
            ]
        }
        mock_manifest_path = tmp_p / "manifest.json"
        mock_manifest_path.write_text(json.dumps(mock_manifest), encoding="utf-8")

        # Test internal function
        res = verify_locked_files(mock_root, mock_manifest)
        assert res["is_intact"] is False
        assert len(res["hash_mismatches"]) == 1
        assert len(res["size_mismatches"]) == 0
        assert res["hash_mismatches"][0]["relative_path"] == file_rel

        # Test CLI execution
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "verify_frontend_lock.py"),
            "--root",
            str(mock_root),
            "--manifest",
            str(mock_manifest_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 1
        assert "VERDICT: VIOLATION" in proc.stdout
        assert "HASH MISMATCHES (TAMPERED FILES)" in proc.stdout
        assert file_rel in proc.stdout


def test_adversarial_size_mismatch():
    """Adversarial Test: Appended bytes trigger SIZE MISMATCH with exit 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_p = Path(tmpdir)
        mock_root = tmp_p / "repo"
        mock_root.mkdir()

        file_rel = "frontend/README.md"
        target = mock_root / file_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"some content + extra byte appended!")

        mock_manifest = {
            "locked_files": [
                {
                    "relative_path": file_rel,
                    "sha256": "0" * 64,
                    "size_bytes": 10,  # Expected 10, actual > 10
                }
            ]
        }
        mock_manifest_path = tmp_p / "manifest.json"
        mock_manifest_path.write_text(json.dumps(mock_manifest), encoding="utf-8")

        res = verify_locked_files(mock_root, mock_manifest)
        assert res["is_intact"] is False
        assert len(res["size_mismatches"]) == 1
        assert res["size_mismatches"][0]["relative_path"] == file_rel
        assert res["size_mismatches"][0]["expected_size"] == 10
        assert res["size_mismatches"][0]["actual_size"] > 10

        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "verify_frontend_lock.py"),
            "--root",
            str(mock_root),
            "--manifest",
            str(mock_manifest_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 1
        assert "SIZE MISMATCHES" in proc.stdout
        assert file_rel in proc.stdout


def test_adversarial_missing_locked_file():
    """Adversarial Test: Deleted / missing locked file triggers MISSING FILES with exit 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_p = Path(tmpdir)
        mock_root = tmp_p / "repo"
        mock_root.mkdir()

        file_rel = "frontend/app.py"
        # Notice: file is NOT created on disk

        mock_manifest = {
            "locked_files": [
                {
                    "relative_path": file_rel,
                    "sha256": "abcdef",
                    "size_bytes": 123,
                }
            ]
        }
        mock_manifest_path = tmp_p / "manifest.json"
        mock_manifest_path.write_text(json.dumps(mock_manifest), encoding="utf-8")

        res = verify_locked_files(mock_root, mock_manifest)
        assert res["is_intact"] is False
        assert len(res["missing_files"]) == 1
        assert res["missing_files"][0]["relative_path"] == file_rel
        assert res["missing_files"][0]["error"] == "File does not exist"

        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "verify_frontend_lock.py"),
            "--root",
            str(mock_root),
            "--manifest",
            str(mock_manifest_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 1
        assert "MISSING FILES" in proc.stdout
        assert file_rel in proc.stdout


def test_adversarial_extraneous_file_in_locked_dir():
    """Adversarial Test: Injecting unauthorized file in frontend/ triggers EXTRANEOUS with exit 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_p = Path(tmpdir)
        mock_root = tmp_p / "repo"
        mock_root.mkdir()

        # Create allowed file
        fe_dir = mock_root / "frontend"
        fe_dir.mkdir()
        (fe_dir / "README.md").write_text("ok", encoding="utf-8")

        # Inject extraneous file
        (fe_dir / "backdoor_component.tsx").write_text("evil()", encoding="utf-8")

        mock_manifest = {
            "locked_files": [
                {
                    "relative_path": "frontend/README.md",
                    "sha256": compute_sha256(fe_dir / "README.md"),
                    "size_bytes": (fe_dir / "README.md").stat().st_size,
                }
            ]
        }
        mock_manifest_path = tmp_p / "manifest.json"
        mock_manifest_path.write_text(json.dumps(mock_manifest), encoding="utf-8")

        res = verify_directory_exclusivity(mock_root, mock_manifest)
        assert res["is_exclusive"] is False
        assert len(res["extraneous_files"]) == 1
        assert res["extraneous_files"][0]["relative_path"] == "frontend/backdoor_component.tsx"

        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "verify_frontend_lock.py"),
            "--root",
            str(mock_root),
            "--manifest",
            str(mock_manifest_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 1
        assert "UNAUTHORIZED / EXTRANEOUS FILES DETECTED" in proc.stdout
        assert "frontend/backdoor_component.tsx" in proc.stdout


def test_adversarial_forbidden_directory_detection():
    """Adversarial Test: Creation of docs/frontend/ with files triggers FORBIDDEN DIRECTORIES with exit 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_p = Path(tmpdir)
        mock_root = tmp_p / "repo"
        mock_root.mkdir()

        # Create forbidden directory
        forbidden = mock_root / "docs" / "frontend"
        forbidden.mkdir(parents=True)
        (forbidden / "rogue.vue").write_text("<template></template>", encoding="utf-8")

        mock_manifest = {"locked_files": []}
        mock_manifest_path = tmp_p / "manifest.json"
        mock_manifest_path.write_text(json.dumps(mock_manifest), encoding="utf-8")

        res = verify_directory_exclusivity(mock_root, mock_manifest)
        assert res["is_exclusive"] is False
        assert len(res["forbidden_directories"]) == 1
        assert res["forbidden_directories"][0]["directory"] == "docs/frontend"

        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "verify_frontend_lock.py"),
            "--root",
            str(mock_root),
            "--manifest",
            str(mock_manifest_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 1
        assert "FORBIDDEN DIRECTORIES DETECTED" in proc.stdout
        assert "docs/frontend" in proc.stdout


def test_adversarial_forbidden_empty_directory_detection():
    """Adversarial Test: Creation of empty docs/frontend/ triggers FORBIDDEN DIRECTORIES with exit 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_p = Path(tmpdir)
        mock_root = tmp_p / "repo"
        mock_root.mkdir()

        # Create forbidden directory empty
        forbidden = mock_root / "docs" / "frontend"
        forbidden.mkdir(parents=True)

        mock_manifest = {"locked_files": []}
        mock_manifest_path = tmp_p / "manifest.json"
        mock_manifest_path.write_text(json.dumps(mock_manifest), encoding="utf-8")

        res = verify_directory_exclusivity(mock_root, mock_manifest)
        assert res["is_exclusive"] is False
        assert len(res["forbidden_directories"]) == 1
        assert res["forbidden_directories"][0]["directory"] == "docs/frontend"
        assert res["forbidden_directories"][0]["extraneous_files"] == []

        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "verify_frontend_lock.py"),
            "--root",
            str(mock_root),
            "--manifest",
            str(mock_manifest_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 1
        assert "VERDICT: VIOLATION" in proc.stdout
        assert "FORBIDDEN DIRECTORIES DETECTED" in proc.stdout
        assert "docs/frontend" in proc.stdout


def test_adversarial_rogue_fe_plan_outside_plans_frontend():
    """Adversarial Test: Creating rogue PLAN-FE-* in docs/plans/ root triggers EXTRANEOUS with exit 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_p = Path(tmpdir)
        mock_root = tmp_p / "repo"
        plans_dir = mock_root / "docs" / "plans"
        plans_dir.mkdir(parents=True)

        rogue_plan = plans_dir / "PLAN-FE-99-ROGUE.md"
        rogue_plan.write_text("# Rogue Plan", encoding="utf-8")

        mock_manifest = {"locked_files": []}
        mock_manifest_path = tmp_p / "manifest.json"
        mock_manifest_path.write_text(json.dumps(mock_manifest), encoding="utf-8")

        res = verify_directory_exclusivity(mock_root, mock_manifest)
        assert res["is_exclusive"] is False
        assert any("PLAN-FE-99-ROGUE.md" in e["relative_path"] for e in res["extraneous_files"])


def test_adversarial_malformed_and_missing_manifest():
    """Adversarial Test: Malformed or missing manifest triggers failure with exit 1."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_p = Path(tmpdir)

        # 1. Non-existent file
        non_existent = tmp_p / "missing.json"
        report1 = execute_verification(PROJECT_ROOT, non_existent)
        assert report1["status"] == "FAIL"
        assert report1["is_valid"] is False

        # 2. Corrupt JSON
        corrupt_json = tmp_p / "corrupt.json"
        corrupt_json.write_text("{ not valid json !!! }", encoding="utf-8")
        report2 = execute_verification(PROJECT_ROOT, corrupt_json)
        assert report2["status"] == "FAIL"
        assert "Failed to parse lock manifest" in report2["error"]

        # 3. JSON without locked_files
        invalid_schema = tmp_p / "no_locked_files.json"
        invalid_schema.write_text('{"foo": "bar"}', encoding="utf-8")
        report3 = execute_verification(PROJECT_ROOT, invalid_schema)
        assert report3["status"] == "FAIL"
        assert "missing 'locked_files'" in report3["error"]


def test_builtin_negative_tests():
    """Verify built-in --negative-test passes all internal adversarial scenarios."""
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "verify_frontend_lock.py"),
        "--negative-test",
    ]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    assert proc.returncode == 0
    assert "All Negative Tests Passed Successfully!" in proc.stdout


def test_zero_mutation_guarantee():
    """Verify that running verification makes zero mutations to existing files."""
    manifest = load_manifest(MANIFEST_PATH)
    locked_files = manifest["locked_files"]

    hashes_before = {}
    for entry in locked_files:
        p = PROJECT_ROOT / entry["relative_path"]
        assert p.is_file(), f"Expected locked file missing: {p}"
        hashes_before[entry["relative_path"]] = compute_sha256(p)

    # Run verification multiple times
    for _ in range(3):
        report = execute_verification(PROJECT_ROOT, MANIFEST_PATH)
        assert report["is_valid"] is True

    # Check hashes afterward
    for entry in locked_files:
        p = PROJECT_ROOT / entry["relative_path"]
        hash_after = compute_sha256(p)
        assert hash_after == hashes_before[entry["relative_path"]], (
            f"File {entry['relative_path']} was mutated during verification!"
        )
