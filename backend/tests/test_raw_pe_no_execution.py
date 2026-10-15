"""TC-03 / PLAN-BE-19: Automated No-Execution Test Suite.

Acceptance Criterion 1: No execution test.
Verifies that X-SENTINEL V3 static raw PE ingestion operates purely in static
analysis mode and NEVER executes, spawns, loads, or detonates input binaries.
"""

from __future__ import annotations

import ast
import math
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from x_sentinel.data.raw_pe import (
    MalformedPEError,
    RawPEFeatureExtractor,
    extract_static_pe,
)

from tests.fixtures.synthetic_pe import (
    build_malformed_pe_variants,
    build_minimal_valid_pe,
)

# ---------------------------------------------------------------------------
# 1. Static AST Analysis of raw_pe.py (Forbidden Primitives Audit)
# ---------------------------------------------------------------------------


def test_ast_forbidden_execution_primitives_absent() -> None:
    """Audit the Abstract Syntax Tree (AST) of raw_pe.py to verify no execution APIs exist."""
    raw_pe_path = Path("backend/src/x_sentinel/data/raw_pe.py")
    assert raw_pe_path.exists(), "raw_pe.py must exist"

    source = raw_pe_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(raw_pe_path))

    forbidden_modules = {
        "subprocess",
        "ctypes",
        "win32process",
        "win32api",
        "win32com",
        "os.system",
        "os.startfile",
        "os.spawn",
        "multiprocessing.Process",
    }

    forbidden_calls = {
        "system",
        "startfile",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "popen",
        "run",
        "call",
        "check_call",
        "check_output",
        "Popen",
        "CreateProcess",
        "CreateProcessA",
        "CreateProcessW",
        "LoadLibrary",
        "LoadLibraryA",
        "LoadLibraryW",
        "ShellExecute",
        "ShellExecuteA",
        "ShellExecuteW",
        "exec",
        "eval",
    }

    # Verify no forbidden module imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert (
                    alias.name not in forbidden_modules
                ), f"Forbidden module '{alias.name}' imported in raw_pe.py"
        elif isinstance(node, ast.ImportFrom):
            assert (
                node.module not in forbidden_modules
            ), f"Forbidden module '{node.module}' imported from in raw_pe.py"

        # Verify no calls to forbidden execution functions
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert (
                    node.func.id not in forbidden_calls
                ), f"Forbidden function call '{node.func.id}()' in raw_pe.py"
            elif isinstance(node.func, ast.Attribute):
                assert (
                    node.func.attr not in forbidden_calls
                ), f"Forbidden method call '{node.func.attr}()' in raw_pe.py"


# ---------------------------------------------------------------------------
# 2. Runtime Execution Primitive Denial Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def execution_denial_guard():
    """Mock all Python process execution and binary loading primitives to fail-closed."""
    mocks = {
        "subprocess_run": patch("subprocess.run", side_effect=AssertionError("EXECUTION FORBIDDEN: subprocess.run")),
        "subprocess_popen": patch("subprocess.Popen", side_effect=AssertionError("EXECUTION FORBIDDEN: subprocess.Popen")),
        "subprocess_call": patch("subprocess.call", side_effect=AssertionError("EXECUTION FORBIDDEN: subprocess.call")),
        "subprocess_check_output": patch("subprocess.check_output", side_effect=AssertionError("EXECUTION FORBIDDEN: subprocess.check_output")),
        "os_system": patch("os.system", side_effect=AssertionError("EXECUTION FORBIDDEN: os.system")),
        "os_popen": patch("os.popen", side_effect=AssertionError("EXECUTION FORBIDDEN: os.popen")),
    }
    # Add os.startfile if on Windows
    if hasattr(os, "startfile"):
        mocks["os_startfile"] = patch("os.startfile", side_effect=AssertionError("EXECUTION FORBIDDEN: os.startfile"))

    for m in mocks.values():
        m.start()
    try:
        yield mocks
    finally:
        for m in mocks.values():
            m.stop()


def test_no_execution_on_valid_pe_parsing(tmp_path: Path, execution_denial_guard) -> None:
    """Verify that parsing a valid PE executes zero subprocesses or system commands."""
    pe_bytes = build_minimal_valid_pe()
    pe_file = tmp_path / "sample.exe"
    pe_file.write_bytes(pe_bytes)

    extractor = RawPEFeatureExtractor(enabled=True, base_dir=tmp_path)
    vector = extractor.extract(pe_file)

    assert len(vector) == 2381
    assert all(isinstance(v, float) and not math.isnan(v) and not math.isinf(v) for v in vector)


def test_no_execution_on_malformed_inputs(tmp_path: Path, execution_denial_guard) -> None:
    """Verify that parsing malformed binaries never triggers fallback execution."""
    extractor = RawPEFeatureExtractor(enabled=True, base_dir=tmp_path)
    variants = build_malformed_pe_variants()

    for name, data in variants.items():
        sample_path = tmp_path / f"malformed_{name}.exe"
        sample_path.write_bytes(data)

        with pytest.raises(MalformedPEError):
            extractor.extract(sample_path)


def test_no_execution_on_direct_byte_extraction(execution_denial_guard) -> None:
    """Verify that in-memory byte extraction executes zero external binaries."""
    pe_bytes = build_minimal_valid_pe()
    vector = extract_static_pe(pe_bytes)

    assert len(vector) == 2381


def test_read_only_file_access(tmp_path: Path) -> None:
    """Verify that file access is strictly read-only and does not modify the target file."""
    pe_bytes = build_minimal_valid_pe()
    pe_file = tmp_path / "readonly_sample.exe"
    pe_file.write_bytes(pe_bytes)

    # Set file read-only on disk
    pe_file.chmod(0o444)

    extractor = RawPEFeatureExtractor(enabled=True, base_dir=tmp_path)
    vector = extractor.extract(pe_file)

    assert len(vector) == 2381
    # Verify file content is completely unchanged
    assert pe_file.read_bytes() == pe_bytes
