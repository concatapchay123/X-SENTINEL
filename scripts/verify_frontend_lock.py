#!/usr/bin/env python3
"""Cryptographic Frontend Lock Verifier for X-SENTINEL V3 (Gate G01).

Enforces the Frontend Lock Contract:
- FRONTEND_STATUS = LOCKED_BY_USER
- FRONTEND_IMPLEMENTATION_ALLOWED = FALSE
- All frontend directories, plans, and documentation artifacts are cryptographically sealed.

Verification checks:
1. Manifest integrity: Load and validate docs/governance/FRONTEND_LOCK_MANIFEST.json.
2. File existence & immutability: Every locked file must exist, match exact byte length, and match SHA-256.
3. Exclusivity & no additions: No extraneous or untracked files in locked directories.
4. Forbidden path containment: docs/frontend/ must not exist or contain unapproved files.
5. Plan scope containment: No unauthorized PLAN-FE-* or TASK-FE-* files outside docs/plans/frontend/.

Exits with:
- 0: Full integrity pass (Gate G01 PASSED).
- 1: Lock breach / tampering / unauthorized additions / missing files (Gate G01 VIOLATION).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


def compute_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file in 64KB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load and parse the cryptographic frontend lock manifest."""
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Lock manifest not found: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "locked_files" not in data:
            raise ValueError("Manifest format invalid: missing 'locked_files' array")
        return data
    except Exception as exc:
        raise ValueError(f"Failed to parse lock manifest: {exc}") from exc


def verify_locked_files(project_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Verify that every file in the manifest exists and matches expected size and hash."""
    locked_files = manifest.get("locked_files", [])
    verified_files = []
    missing_files = []
    hash_mismatches = []
    size_mismatches = []

    for entry in locked_files:
        rel_path = entry.get("relative_path", "")
        expected_hash = entry.get("sha256", "").lower()
        expected_size = entry.get("size_bytes")

        target = project_root / rel_path
        if not target.is_file():
            missing_files.append({
                "relative_path": rel_path,
                "error": "File does not exist"
            })
            continue

        actual_size = target.stat().st_size
        if expected_size is not None and actual_size != expected_size:
            size_mismatches.append({
                "relative_path": rel_path,
                "expected_size": expected_size,
                "actual_size": actual_size
            })

        actual_hash = compute_sha256(target).lower()
        if actual_hash != expected_hash:
            hash_mismatches.append({
                "relative_path": rel_path,
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash
            })
        else:
            verified_files.append(rel_path)

    return {
        "total_expected": len(locked_files),
        "verified_count": len(verified_files),
        "missing_files": missing_files,
        "hash_mismatches": hash_mismatches,
        "size_mismatches": size_mismatches,
        "is_intact": not missing_files and not hash_mismatches and not size_mismatches
    }


def verify_directory_exclusivity(project_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Ensure no unauthorized files were added to locked frontend directories."""
    locked_files = manifest.get("locked_files", [])
    allowed_rel_paths = {entry["relative_path"].replace("\\", "/") for entry in locked_files}
    extraneous_files = []
    forbidden_directories = []

    # Directories that are strictly locked and must not contain any untracked files
    locked_dir_paths = [
        "frontend",
        "docs/frontend-handoff",
        "docs/plans/frontend"
    ]

    for d in locked_dir_paths:
        dir_full = project_root / d
        if not dir_full.exists():
            continue
        for root, _, files in os.walk(dir_full):
            for file in files:
                full_file = Path(root) / file
                rel_posix = full_file.relative_to(project_root).as_posix()
                if rel_posix not in allowed_rel_paths:
                    extraneous_files.append({
                        "relative_path": rel_posix,
                        "parent_dir": d,
                        "error": "Extraneous / unauthorized file in locked directory"
                    })

    # Forbidden unapproved directories: docs/frontend
    forbidden_dir = project_root / "docs" / "frontend"
    if forbidden_dir.exists():
        found_files = [p.relative_to(project_root).as_posix() for p in forbidden_dir.rglob("*") if p.is_file()]
        forbidden_directories.append({
            "directory": "docs/frontend",
            "extraneous_files": found_files,
            "error": "Forbidden uncreated directory docs/frontend exists on filesystem"
        })

    # Search for any rogue PLAN-FE-* or TASK-FE-* files anywhere in docs/plans/ outside docs/plans/frontend
    plans_dir = project_root / "docs" / "plans"
    if plans_dir.exists():
        for p in plans_dir.rglob("*"):
            if p.is_file() and ("PLAN-FE-" in p.name.upper() or "TASK-FE-" in p.name.upper()):
                rel = p.relative_to(project_root).as_posix()
                if rel not in allowed_rel_paths:
                    extraneous_files.append({
                        "relative_path": rel,
                        "parent_dir": "docs/plans",
                        "error": "Unauthorized frontend plan outside locked docs/plans/frontend/"
                    })

    return {
        "extraneous_files": extraneous_files,
        "forbidden_directories": forbidden_directories,
        "is_exclusive": not extraneous_files and not forbidden_directories
    }


def execute_verification(project_root: Path, manifest_path: Path) -> dict[str, Any]:
    """Execute complete cryptographic verification and directory containment checks."""
    try:
        manifest = load_manifest(manifest_path)
    except Exception as exc:
        return {
            "status": "FAIL",
            "error": str(exc),
            "gate": "Gate G01: Source Integrity & Frontend Lock",
            "is_valid": False
        }

    file_results = verify_locked_files(project_root, manifest)
    dir_results = verify_directory_exclusivity(project_root, manifest)

    is_valid = file_results["is_intact"] and dir_results["is_exclusive"]
    status = "PASS" if is_valid else "FAIL"

    return {
        "status": status,
        "gate": manifest.get("governance", {}).get("enforcement_gate", "Gate G01: Source Integrity & Frontend Lock"),
        "manifest_name": manifest.get("manifest_name", "Frontend Lock Manifest"),
        "manifest_version": manifest.get("version", "1.0.0"),
        "manifest_created_at": manifest.get("created_at", "UNKNOWN"),
        "total_locked_files": file_results["total_expected"],
        "verified_count": file_results["verified_count"],
        "missing_count": len(file_results["missing_files"]),
        "hash_mismatch_count": len(file_results["hash_mismatches"]),
        "size_mismatch_count": len(file_results["size_mismatches"]),
        "extraneous_count": len(dir_results["extraneous_files"]),
        "forbidden_dir_count": len(dir_results["forbidden_directories"]),
        "details": {
            "missing_files": file_results["missing_files"],
            "hash_mismatches": file_results["hash_mismatches"],
            "size_mismatches": file_results["size_mismatches"],
            "extraneous_files": dir_results["extraneous_files"],
            "forbidden_directories": dir_results["forbidden_directories"]
        },
        "is_valid": is_valid
    }


def run_negative_tests(project_root: Path, valid_manifest_path: Path) -> bool:
    """Run simulated tampering and negative containment tests."""
    print("Running Negative Verification & Adversarial Tests...")
    manifest = load_manifest(valid_manifest_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_p = Path(tmpdir)

        # 1. Tampered hash test
        tampered_manifest = dict(manifest)
        tampered_locked = [dict(f) for f in manifest["locked_files"]]
        tampered_locked[0]["sha256"] = "0" * 64
        tampered_manifest["locked_files"] = tampered_locked
        tampered_path = tmp_p / "tampered_manifest.json"
        tampered_path.write_text(json.dumps(tampered_manifest), encoding="utf-8")

        res1 = execute_verification(project_root, tampered_path)
        if res1["status"] != "FAIL" or res1["hash_mismatch_count"] != 1:
            print("[-] FAILED: Tampered hash detection test failed.")
            return False
        print("[+] PASSED: Tampered hash correctly detected.")

        # 2. Missing file test
        missing_manifest = dict(manifest)
        missing_locked = [dict(f) for f in manifest["locked_files"]]
        missing_locked.append({
            "relative_path": "frontend/rogue_component.tsx",
            "category": "frontend_runtime",
            "size_bytes": 100,
            "sha256": "a" * 64
        })
        missing_manifest["locked_files"] = missing_locked
        missing_path = tmp_p / "missing_manifest.json"
        missing_path.write_text(json.dumps(missing_manifest), encoding="utf-8")

        res2 = execute_verification(project_root, missing_path)
        if res2["status"] != "FAIL" or res2["missing_count"] != 1:
            print("[-] FAILED: Missing file detection test failed.")
            return False
        print("[+] PASSED: Missing locked file correctly detected.")

        # 3. Size mismatch test
        size_manifest = dict(manifest)
        size_locked = [dict(f) for f in manifest["locked_files"]]
        size_locked[0]["size_bytes"] = size_locked[0]["size_bytes"] + 9999
        size_manifest["locked_files"] = size_locked
        size_path = tmp_p / "size_manifest.json"
        size_path.write_text(json.dumps(size_manifest), encoding="utf-8")

        res3 = execute_verification(project_root, size_path)
        if res3["status"] != "FAIL" or res3["size_mismatch_count"] != 1:
            print("[-] FAILED: Size mismatch detection test failed.")
            return False
        print("[+] PASSED: Size mismatch correctly detected.")

        # 4. Extraneous file in locked directory test
        mock_root = tmp_p / "mock_root"
        mock_fe = mock_root / "frontend"
        mock_fe.mkdir(parents=True)
        (mock_fe / "README.md").write_text("x", encoding="utf-8")
        (mock_fe / "app.py").write_text("x", encoding="utf-8")
        (mock_fe / "rogue_script.js").write_text("alert(1)", encoding="utf-8")
        res4 = verify_directory_exclusivity(mock_root, manifest)
        if res4["is_exclusive"] or len(res4["extraneous_files"]) != 1:
            print("[-] FAILED: Extraneous file detection test failed.")
            return False
        print("[+] PASSED: Extraneous file in locked directory correctly detected.")

        # 5. Forbidden docs/frontend directory test (empty and populated)
        mock_forbidden = mock_root / "docs" / "frontend"
        mock_forbidden.mkdir(parents=True)
        # 5a. Empty directory check
        res5_empty = verify_directory_exclusivity(mock_root, manifest)
        if res5_empty["is_exclusive"] or len(res5_empty["forbidden_directories"]) != 1:
            print("[-] FAILED: Forbidden empty directory detection test failed.")
            return False
        # 5b. Populated directory check
        (mock_forbidden / "unapproved_page.html").write_text("<h1>Hack</h1>", encoding="utf-8")
        res5 = verify_directory_exclusivity(mock_root, manifest)
        if res5["is_exclusive"] or len(res5["forbidden_directories"]) != 1:
            print("[-] FAILED: Forbidden directory detection test failed.")
            return False
        print("[+] PASSED: Forbidden docs/frontend directory correctly detected.")

    print("All Negative Tests Passed Successfully!")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify cryptographic lock on all frontend artifacts (Gate G01)."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path to FRONTEND_LOCK_MANIFEST.json"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Path to project root directory"
    )
    parser.add_argument(
        "--negative-test",
        action="store_true",
        help="Execute simulated negative tests (tampered hash, missing files)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON verification results"
    )

    args = parser.parse_args()

    # Determine project root
    if args.root:
        project_root = args.root.resolve()
    else:
        # Default: script is in scripts/ -> parent of parent is root
        script_dir = Path(__file__).resolve().parent
        if script_dir.name == "scripts":
            project_root = script_dir.parent
        else:
            # Fallback to current working directory
            project_root = Path.cwd().resolve()

    # Determine manifest path
    if args.manifest:
        manifest_path = args.manifest.resolve()
    else:
        default_governance = project_root / "docs" / "governance" / "FRONTEND_LOCK_MANIFEST.json"
        fallback_agent = project_root / ".agents" / "teamwork" / "explorer_survey_r1_frontend_lock" / "FRONTEND_LOCK_MANIFEST.json"
        if default_governance.is_file():
            manifest_path = default_governance
        elif fallback_agent.is_file():
            manifest_path = fallback_agent
        else:
            manifest_path = default_governance

    if args.negative_test:
        if not manifest_path.is_file():
            print(f"Error: Base manifest not found at {manifest_path}", file=sys.stderr)
            return 1
        ok = run_negative_tests(project_root, manifest_path)
        return 0 if ok else 1

    report = execute_verification(project_root, manifest_path)

    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if report["is_valid"] else 1

    print("=" * 80)
    print("X-SENTINEL V3 — GATE G01 FRONTEND CRYPTOGRAPHIC LOCK VERIFICATION")
    print("=" * 80)
    print(f"Project Root       : {project_root}")
    print(f"Lock Manifest      : {manifest_path}")
    print(f"Manifest Version   : {report.get('manifest_version', 'N/A')}")
    print(f"Created At         : {report.get('manifest_created_at', 'N/A')}")
    print(f"Total Locked Files : {report.get('total_locked_files', 0)}")
    print(f"Verified Intact    : {report.get('verified_count', 0)}")
    print(f"Missing Files      : {report.get('missing_count', 0)}")
    print(f"Hash Mismatches    : {report.get('hash_mismatch_count', 0)}")
    print(f"Size Mismatches    : {report.get('size_mismatch_count', 0)}")
    print(f"Extraneous Files   : {report.get('extraneous_count', 0)}")
    print(f"Forbidden Dirs     : {report.get('forbidden_dir_count', 0)}")
    print("-" * 80)

    if report["is_valid"]:
        print("VERDICT: PASS — Gate G01: Source Integrity & Frontend Lock is 100% SATISFIED.")
        print("All frontend directories, plans, and files are sealed and unchanged.")
        print("=" * 80)
        return 0
    else:
        print("VERDICT: VIOLATION — Gate G01 FAILED!")
        details = report.get("details", {})
        if details.get("missing_files"):
            print("\n[!] MISSING FILES:")
            for m in details["missing_files"]:
                print(f"  - {m['relative_path']}")
        if details.get("hash_mismatches"):
            print("\n[!] HASH MISMATCHES (TAMPERED FILES):")
            for h in details["hash_mismatches"]:
                print(f"  - {h['relative_path']}")
                print(f"      Expected: {h['expected_sha256']}")
                print(f"      Actual  : {h['actual_sha256']}")
        if details.get("size_mismatches"):
            print("\n[!] SIZE MISMATCHES:")
            for s in details["size_mismatches"]:
                print(f"  - {s['relative_path']} (Expected: {s['expected_size']}, Actual: {s['actual_size']})")
        if details.get("extraneous_files"):
            print("\n[!] UNAUTHORIZED / EXTRANEOUS FILES DETECTED:")
            for e in details["extraneous_files"]:
                print(f"  - {e['relative_path']} in {e['parent_dir']}")
        if details.get("forbidden_directories"):
            print("\n[!] FORBIDDEN DIRECTORIES DETECTED:")
            for f in details["forbidden_directories"]:
                print(f"  - {f['directory']}: {len(f['extraneous_files'])} file(s)")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
