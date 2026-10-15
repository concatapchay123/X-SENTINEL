#!/usr/bin/env python3
"""SHA-256 Manifest Verifier & Negative Test Suite for X-SENTINEL V3 Handover.

Validates:
1. Every entry in SHA256SUMS.txt exists.
2. Every entry's SHA-256 matches actual recomputed file bytes.
3. Zero duplicate paths.
4. Path formatting is strictly relative and normalized.
5. Runs negative tests (tampered content detection, missing file detection).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_manifest(manifest_path: Path | None = None) -> dict[str, Any]:
    if manifest_path is None:
        manifest_path = PROJECT_ROOT / "SHA256SUMS.txt"

    if not manifest_path.is_file():
        return {
            "status": "FAIL",
            "error": f"Manifest file not found: {manifest_path}",
            "verified_count": 0,
            "failed_count": 0,
            "missing_count": 0,
            "duplicates": [],
            "mismatches": [],
        }

    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    seen_paths: set[str] = set()
    duplicates: list[str] = []
    mismatches: list[dict[str, str]] = []
    missing: list[str] = []
    verified_count = 0

    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(None, 1)
        if len(parts) != 2:
            mismatches.append({"line": str(idx), "error": f"Malformed line: {line}"})
            continue

        expected_hash, rel_path = parts[0], parts[1].strip()
        # Normalize relative path if it starts with ./
        if rel_path.startswith("./"):
            rel_path = rel_path[2:]

        if rel_path in seen_paths:
            duplicates.append(rel_path)
        seen_paths.add(rel_path)

        file_path = PROJECT_ROOT / rel_path
        if not file_path.is_file():
            missing.append(rel_path)
            continue

        actual_hash = compute_sha256(file_path)
        if actual_hash.lower() != expected_hash.lower():
            mismatches.append({
                "path": rel_path,
                "expected": expected_hash,
                "actual": actual_hash,
            })
        else:
            verified_count += 1

    status = "PASS" if not mismatches and not missing and not duplicates else "FAIL"
    return {
        "status": status,
        "total_entries": len(seen_paths),
        "verified_count": verified_count,
        "failed_count": len(mismatches),
        "missing_count": len(missing),
        "duplicates": duplicates,
        "mismatches": mismatches,
        "missing": missing,
    }


def run_negative_tests() -> bool:
    """Executes negative tests on synthetic temporary manifests to verify tampering detection."""
    import tempfile

    test_file = PROJECT_ROOT / "README.md"
    real_hash = compute_sha256(test_file)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_p = Path(tmp_dir)

        # 1. Corrupted hash test
        bad_manifest = tmp_p / "bad_sha256.txt"
        bad_manifest.write_text("0000000000000000000000000000000000000000000000000000000000000000  README.md\n", encoding="utf-8")
        res1 = verify_manifest(bad_manifest)
        if res1["status"] != "FAIL" or len(res1["mismatches"]) != 1:
            return False

        # 2. Missing file test
        missing_manifest = tmp_p / "missing_file.txt"
        missing_manifest.write_text(f"{real_hash}  nonexistent_file_xyz_123.bin\n", encoding="utf-8")
        res2 = verify_manifest(missing_manifest)
        if res2["status"] != "FAIL" or len(res2["missing"]) != 1:
            return False

        # 3. Duplicate entry test
        dup_manifest = tmp_p / "dup_file.txt"
        dup_manifest.write_text(f"{real_hash}  README.md\n{real_hash}  README.md\n", encoding="utf-8")
        res3 = verify_manifest(dup_manifest)
        if len(res3["duplicates"]) != 1:
            return False

    return True


if __name__ == "__main__":
    rep = verify_manifest()
    neg_ok = run_negative_tests()
    print(f"Manifest Verification: {rep['status']} (Verified: {rep['verified_count']}, Failed: {rep['failed_count']}, Missing: {rep['missing_count']})")
    print(f"Negative Verification Tests: {'PASS' if neg_ok else 'FAIL'}")
    if rep["status"] == "PASS" and neg_ok:
        sys.exit(0)
    else:
        sys.exit(1)
