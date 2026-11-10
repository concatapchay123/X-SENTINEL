"""Regression tests for Batch C: F04 (release tuple verification), F11 (docker-compose migrate),

F12 (CI ODBC driver), and F16 (.gitattributes).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_f04_verify_release_tuple_draft_and_strict():
    """Verify that verify_release_tuple detects unverified image/model and fails closed on strict."""
    # Test verify-only (returns 0 with DRAFT warning when image/model missing)
    res_draft = subprocess.run(
        [sys.executable, "scripts/verify_release_tuple.py", "--verify-only"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_draft.returncode == 0
    assert "DRAFT/UNVERIFIED STATE" in res_draft.stderr or "DRAFT/UNVERIFIED STATE" in res_draft.stdout

    # Test strict mode (must return 1 because model weights are not in git)
    res_strict = subprocess.run(
        [sys.executable, "scripts/verify_release_tuple.py", "--strict"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_strict.returncode == 1
    assert "STRICT CHECK FAILED" in res_strict.stderr or "STRICT CHECK FAILED" in res_strict.stdout


def test_f04_verify_release_tuple_require_model():
    """Verify that --require-model flag fails closed when model weights are missing."""
    res = subprocess.run(
        [sys.executable, "scripts/verify_release_tuple.py", "--require-model"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 1
    assert "Model weights required but not found" in res.stderr or "Model weights required but not found" in res.stdout


def test_f11_docker_compose_migrate_command():
    """Verify that docker-compose.yml runs ensure_database.py before alembic migration."""
    compose_path = PROJECT_ROOT / "docker-compose.yml"
    assert compose_path.is_file()
    content = compose_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    migrate_service = data["services"]["migrate"]
    cmd = migrate_service["command"]
    cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
    assert "ensure_database.py" in cmd_str, f"migrate command missing ensure_database.py: {cmd_str}"
    assert "alembic" in cmd_str, f"migrate command missing alembic: {cmd_str}"


def test_f12_ci_workflow_installs_msodbcsql17():
    """Verify that .github/workflows/ci.yml installs msodbcsql17."""
    ci_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    assert ci_path.is_file()
    content = ci_path.read_text(encoding="utf-8")
    assert "msodbcsql17" in content, "CI workflow does not install msodbcsql17"
    assert "packages.microsoft.com" in content, "CI workflow missing Microsoft package repository"


def test_f16_gitattributes_exists_and_sets_lf():
    """Verify that .gitattributes enforces LF line endings across the repository."""
    gitattributes_path = PROJECT_ROOT / ".gitattributes"
    assert gitattributes_path.is_file(), ".gitattributes file is missing"
    content = gitattributes_path.read_text(encoding="utf-8")
    assert "* text=auto eol=lf" in content, ".gitattributes missing '* text=auto eol=lf'"
    assert "*.sh text eol=lf" in content, ".gitattributes missing '*.sh text eol=lf'"
