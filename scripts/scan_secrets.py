#!/usr/bin/env python3
"""Automated repository secret scanning utility for X-SENTINEL V3 (PLAN-BE-15).

Scans source code, configuration files, documentation, scripts, and tracked artifacts
for hardcoded credentials, private keys, database passwords, and high-entropy API tokens.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend/src to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "backend" / "src"))

from x_sentinel.security.secrets import scan_directory_for_secrets  # noqa: E402


def run_secret_scan(target_dir: Path | None = None) -> int:
    root = target_dir or repo_root
    print(f"[*] Starting X-SENTINEL V3 automated secret scan on: {root}")

    findings = scan_directory_for_secrets(
        root=root,
        exclude_dirs=(
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            "node_modules",
            ".venv",
            "venv",
            ".gemini",
            "artifacts",
        ),
        allowed_extensions=(
            ".py",
            ".yaml",
            ".yml",
            ".json",
            ".env",
            ".env.example",
            ".sh",
            ".sql",
            ".md",
            ".toml",
        ),
        ignore_synthetic=True,
    )

    print(f"[*] Scan completed. Total potential findings: {len(findings)}")

    if not findings:
        print("[+] SUCCESS: No exposed production credentials discovered. Secret scan PASS.")
        return 0

    print("[-] WARNING: Credential findings detected:")
    for f in findings:
        print(f"  - [{f.severity}] {f.secret_type} at {f.file_path}:{f.line_number}")
        print(f"    Snippet: {f.masked_snippet}")

    critical_count = sum(1 for f in findings if f.severity in {"P0_CRITICAL", "P1_HIGH"})
    if critical_count > 0:
        print(f"[-] FAILED: Found {critical_count} critical/high secret exposure(s).")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run_secret_scan())
