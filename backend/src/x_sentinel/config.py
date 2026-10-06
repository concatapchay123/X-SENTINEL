from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="XS_", env_file=".env", extra="ignore")

    env: str = "development"
    demo_mode: bool = True
    log_level: str = "INFO"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_port: int = 8501
    api_base_url: str = "http://localhost:8000"
    input_mode: str = "vector"
    config_dir: Path = Path("configs")
    artifact_dir: Path = Path("artifacts")
    model_dir: Path = Path("models")
    audit_log_path: Path = Path("artifacts/audit/events.jsonl")

    database_url: str = (
        "mssql+pyodbc://localhost/xsentinel?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
    )
    database_required: bool = True
    expected_db_revision: str = "0002_v3_jev_ai_audit"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle_seconds: int = 1800

    api_auth_mode: str = "none"
    allowed_origins: str = "http://localhost:8501"
    max_upload_bytes: int = 52_428_800

    jev_ai_enabled: bool = False
    jev_ai_base_url: str = "http://localhost:1234/v1"
    jev_ai_model: str = "jev-local-TBD"
    jev_ai_timeout_seconds: float = 60.0
    jev_ai_temperature: float = 0.1
    jev_ai_max_context_chars: int = 30_000
    jev_ai_prompt_version: str = "jev-v3.0.0"
    jev_ai_advisory_only: bool = True
    jev_ai_local_only: bool = True
    jev_ai_store_response_text: bool = True
    jev_ai_store_prompt_text: bool = False

    research_asr_gate: float = 0.50
    production_asr_target: float = 0.80
    fpr_target: float = 0.01
    latency_p95_ms_target: float = 10.0
    circuit_breaker_ms: float = 8.0

    def load_yaml_config(self, filename: str) -> dict[str, Any]:
        path = self.config_dir / filename
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def get_jev_ai_config(self) -> dict[str, Any]:
        return self.load_yaml_config("jev_ai.yaml")


settings = Settings()
