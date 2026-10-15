#!/usr/bin/env python3
"""Deterministic SHA-256 Checksum Generator for X-SENTINEL V3 Handover.

Generates SHA256SUMS.txt matching canonical handover criteria:
- Deterministic relative forward-slash paths
- Stable lexical sorting
- Exclusion of VCS, caches, temporary files, local virtualenvs, and sensitive local datasets
- Calculation directly from actual file bytes
- Excludes SHA256SUMS.txt itself to prevent circular reference
"""

from __future__ import annotations

import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
}

EXCLUDE_FILES = {
    "SHA256SUMS.txt",
    ".coverage",
}


def should_include(rel_path: str) -> bool:
    parts = rel_path.replace("\\", "/").split("/")
    # Exclude directories
    for part in parts[:-1]:
        if part in EXCLUDE_DIRS:
            return False

    filename = parts[-1]
    if filename in EXCLUDE_FILES:
        return False
    if filename.endswith(".pyc") or filename.endswith(".pyo"):
        return False

    # Exclude dataset contents except .gitkeep
    if len(parts) > 1 and parts[0] == "datasets" and filename != ".gitkeep":
        return False

    return True


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_manifest(output_file: Path | None = None) -> list[tuple[str, str]]:
    if output_file is None:
        output_file = PROJECT_ROOT / "SHA256SUMS.txt"

    entries: list[tuple[str, str]] = []

    for file_path in PROJECT_ROOT.rglob("*"):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(PROJECT_ROOT).as_posix()
        if should_include(rel):
            digest = compute_file_sha256(file_path)
            entries.append((digest, rel))

    # Sort stably by relative path
    entries.sort(key=lambda x: x[1])

    lines = [f"{digest}  {rel}\n" for digest, rel in entries]
    output_file.write_text("".join(lines), encoding="utf-8")
    return entries


if __name__ == "__main__":
    entries = generate_manifest()
    print(f"Generated SHA256SUMS.txt with {len(entries)} verified entries.")
