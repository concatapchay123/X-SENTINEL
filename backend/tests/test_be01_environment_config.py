from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from x_sentinel.config import Settings, settings
from x_sentinel.jev_ai.guardrails import (
    JevContextBlocked,
    validate_context,
    validate_local_endpoint,
)


ROOT_DIR = Path(__file__).resolve().parents[2]


def test_settings_load_defaults() -> None:
    s = Settings()
    assert s.env == "development"
    assert s.demo_mode is True
    assert s.input_mode == "vector"
    assert s.database_required is True
    assert s.expected_db_revision == "0002_v3_jev_ai_audit"
    assert s.jev_ai_enabled is False
    assert s.jev_ai_advisory_only is True
    assert s.jev_ai_local_only is True
    assert s.jev_ai_base_url == "http://localhost:1234/v1"
    assert s.jev_ai_model == "jev-local-TBD"
    assert s.jev_ai_prompt_version == "jev-v3.0.0"


def test_env_example_contains_all_core_settings() -> None:
    env_example_path = ROOT_DIR / ".env.example"
    assert env_example_path.exists(), ".env.example must exist"
    content = env_example_path.read_text(encoding="utf-8")

    expected_keys = [
        "XS_ENV",
        "XS_DEMO_MODE",
        "XS_INPUT_MODE",
        "XS_BACKEND_PORT",
        "XS_FRONTEND_PORT",
        "XS_DATABASE_URL",
        "XS_DATABASE_REQUIRED",
        "XS_EXPECTED_DB_REVISION",
        "XS_JEV_AI_ENABLED",
        "XS_JEV_AI_BASE_URL",
        "XS_JEV_AI_MODEL",
        "XS_JEV_AI_ADVISORY_ONLY",
        "XS_JEV_AI_LOCAL_ONLY",
        "XS_RESEARCH_ASR_GATE",
        "XS_PRODUCTION_ASR_TARGET",
        "XS_FPR_TARGET",
    ]
    for key in expected_keys:
        assert key in content, f"{key} missing in .env.example"


def test_jev_ai_yaml_contract() -> None:
    config_path = ROOT_DIR / "configs/jev_ai.yaml"
    assert config_path.exists(), "configs/jev_ai.yaml must exist"
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert data.get("version") == "v3"
    assert data.get("enabled") is False
    assert data.get("advisory_only") is True
    assert data.get("provider") == "lm_studio_openai_compatible"
    assert data.get("base_url") == "http://localhost:1234/v1"
    assert data.get("model_id") == "jev-local-TBD"

    security = data.get("security", {})
    assert security.get("local_only") is True
    allowed_hosts = set(security.get("allowed_hosts", []))
    assert {"localhost", "127.0.0.1", "host.docker.internal"}.issubset(allowed_hosts)

    context_cfg = data.get("context", {})
    assert context_cfg.get("allow_raw_features") is False
    assert context_cfg.get("allow_raw_pe") is False


def test_dataset_exclusion_policies() -> None:
    gitignore_path = ROOT_DIR / ".gitignore"
    assert gitignore_path.exists(), ".gitignore must exist"
    gi_content = gitignore_path.read_text(encoding="utf-8")
    assert "datasets/*" in gi_content, ".gitignore must exclude datasets/*"
    assert "!datasets/.gitkeep" in gi_content, ".gitignore must preserve !datasets/.gitkeep"

    dockerignore_path = ROOT_DIR / ".dockerignore"
    assert dockerignore_path.exists(), ".dockerignore must exist"
    di_content = dockerignore_path.read_text(encoding="utf-8")
    assert "datasets/**" in di_content, ".dockerignore must exclude datasets/**"
    assert "!datasets/.gitkeep" in di_content, ".dockerignore must preserve !datasets/.gitkeep"

    gitkeep_path = ROOT_DIR / "datasets/.gitkeep"
    assert gitkeep_path.exists(), "datasets/.gitkeep must exist to preserve empty directory in repo"


def test_local_datasets_are_preserved_not_deleted() -> None:
    datasets_dir = ROOT_DIR / "datasets"
    assert datasets_dir.exists(), "datasets directory must exist"
    # Verify that existing datasets directories (e.g. ember2018, bodmas) are intact
    expected_subdirs = ["ember2018", "bodmas"]
    for subdir in expected_subdirs:
        subpath = datasets_dir / subdir
        if subpath.exists():
            assert subpath.is_dir(), f"{subdir} should be a directory"


def test_guardrails_strictly_block_cloud_llms() -> None:
    cloud_urls = [
        "https://api.openai.com/v1",
        "https://api.anthropic.com/v1",
        "https://generativelanguage.googleapis.com/v1",
        "http://192.168.1.100:1234/v1",
        "http://8.8.8.8:1234/v1",
        "https://my-cloud-llm.azure.com",
    ]
    for url in cloud_urls:
        with pytest.raises(JevContextBlocked):
            validate_local_endpoint(url)

    allowed_local_urls = [
        "http://localhost:1234/v1",
        "http://127.0.0.1:1234/v1",
        "http://host.docker.internal:1234/v1",
    ]
    for url in allowed_local_urls:
        validate_local_endpoint(url)


def test_guardrails_block_forbidden_and_oversized_payloads() -> None:
    forbidden_payloads = [
        {"blind_label": 1},
        {"ground_truth": "malicious"},
        {"trigger_manifest": {"signature": "abc"}},
        {"hidden_manifest": True},
        {"raw_pe": "MZ..."},
        {"raw_binary": b"MZ"},
        {"api_key": "sk-12345"},
        {"password": "secret"},
        {"database_url": "mssql+pyodbc://sa:pass@localhost/db"},
    ]
    for payload in forbidden_payloads:
        with pytest.raises(JevContextBlocked):
            validate_context(payload)

    oversized = {"text": "A" * 35_000}
    with pytest.raises(JevContextBlocked):
        validate_context(oversized, max_chars=30_000)


def test_settings_load_yaml_config() -> None:
    s = Settings(config_dir=ROOT_DIR / "configs")
    jev_cfg = s.get_jev_ai_config()
    assert jev_cfg.get("version") == "v3"
    assert jev_cfg.get("enabled") is False
    assert jev_cfg.get("model_id") == "jev-local-TBD"

    detector_cfg = s.load_yaml_config("detector.yaml")
    assert detector_cfg.get("status") == "PARTIAL_BASELINE"


def test_baseline_audit_and_validation_scripts() -> None:
    import subprocess
    import sys

    # baseline_audit.py execution
    res_audit = subprocess.run(
        [sys.executable, str(ROOT_DIR / "scripts/baseline_audit.py")],
        capture_output=True,
        text=True,
    )
    assert res_audit.returncode == 0, f"baseline_audit failed: {res_audit.stderr}"
    assert "BASELINE AUDIT PASS" in res_audit.stdout

    # validate_v3_package.py execution
    res_val = subprocess.run(
        [sys.executable, str(ROOT_DIR / "scripts/validate_v3_package.py")],
        capture_output=True,
        text=True,
    )
    assert res_val.returncode == 0, f"validate_v3_package failed: {res_val.stderr}"
    assert "PASS" in res_val.stdout
