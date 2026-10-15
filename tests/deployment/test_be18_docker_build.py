from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestDockerBuildArchitecture:
    """Verifies Dockerfile configurations, non-root users, dependencies, and hardening."""

    def test_backend_dockerfile_exists_and_uses_non_root(self) -> None:
        dockerfile = PROJECT_ROOT / "infrastructure" / "docker" / "backend.Dockerfile"
        assert dockerfile.exists(), "backend.Dockerfile must exist"
        content = dockerfile.read_text(encoding="utf-8")

        # Base image must be pinned (python:3.11-slim-bookworm)
        assert "FROM python:3.11-slim-bookworm" in content
        # Non-root user setup
        assert "groupadd -g 10001 appgroup" in content
        assert "useradd -u 10001 -g appgroup -m -s /bin/bash appuser" in content
        assert "USER appuser" in content
        # Native dependencies for LightGBM and SQL Server ODBC
        assert "msodbcsql17" in content or "msodbcsql18" in content
        assert "unixodbc" in content
        assert "libgomp1" in content
        # Port exposure and healthcheck
        assert "EXPOSE 8000" in content
        assert "HEALTHCHECK" in content
        assert "/ready" in content

    def test_frontend_dockerfile_exists_and_uses_non_root(self) -> None:
        dockerfile = PROJECT_ROOT / "infrastructure" / "docker" / "frontend.Dockerfile"
        assert dockerfile.exists(), "frontend.Dockerfile must exist"
        content = dockerfile.read_text(encoding="utf-8")

        assert "FROM python:3.11-slim-bookworm" in content
        assert "groupadd -g 10001 appgroup" in content
        assert "useradd -u 10001 -g appgroup" in content
        assert "USER appuser" in content
        assert "EXPOSE 8501" in content
        assert "HEALTHCHECK" in content
        assert "_stcore/health" in content

    def test_dockerignore_excludes_secrets_and_blind_manifests(self) -> None:
        dockerignore = PROJECT_ROOT / ".dockerignore"
        assert dockerignore.exists(), ".dockerignore must exist"
        content = dockerignore.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

        # Prohibited elements must be ignored
        assert ".git" in lines
        assert ".env" in lines
        assert "*.key" in lines or "*.pem" in lines
        assert "datasets/**" in lines
        assert "data/private/**" in lines
        assert "blind_evaluation/**" in lines
        assert "*blind*manifest*" in lines
        assert "*poisoning*manifest*" in lines
        assert "*hidden_manifest*" in lines

        # Critical application code must NOT be ignored
        assert "!backend/src/x_sentinel/security/secrets.py" in lines
        assert "!scripts/scan_secrets.py" in lines


class TestDockerComposeArchitecture:
    """Verifies docker-compose.yml service topology, networking, limits, and volumes."""

    def test_compose_services_and_topology(self) -> None:
        compose_file = PROJECT_ROOT / "docker-compose.yml"
        assert compose_file.exists(), "docker-compose.yml must exist"
        data = yaml.safe_load(compose_file.read_text(encoding="utf-8"))

        services = data.get("services", {})
        assert "mssql" in services, "mssql service required"
        assert "migrate" in services, "migrate service required"
        assert "backend" in services, "backend service required"
        assert "frontend" in services, "frontend service required"

        # Dedicated isolated bridge network
        networks = data.get("networks", {})
        assert "xsentinel_net" in networks
        assert networks["xsentinel_net"]["driver"] == "bridge"

        # Check dependency ordering
        assert services["backend"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
        assert services["frontend"]["depends_on"]["backend"]["condition"] == "service_healthy"

    def test_compose_security_and_resource_limits(self) -> None:
        compose_file = PROJECT_ROOT / "docker-compose.yml"
        data = yaml.safe_load(compose_file.read_text(encoding="utf-8"))
        services = data["services"]

        # Backend volumes: configs and models read-only, artifacts writable
        be_volumes = services["backend"]["volumes"]
        assert "./configs:/app/configs:ro" in be_volumes
        assert "./models:/app/models:ro" in be_volumes
        assert "./artifacts:/app/artifacts" in be_volumes

        # Resource limits defined to prevent starvation or out-of-memory cascades
        be_res = services["backend"].get("deploy", {}).get("resources", {})
        assert "limits" in be_res
        assert be_res["limits"]["cpus"] == "4.0"
        assert be_res["limits"]["memory"] == "4096M"

        # Host gateway mapping for local host LM Studio
        extra_hosts = services["backend"].get("extra_hosts", [])
        assert "host.docker.internal:host-gateway" in extra_hosts

    def test_compose_env_file_is_safe_and_optional(self) -> None:
        compose_file = PROJECT_ROOT / "docker-compose.yml"
        data = yaml.safe_load(compose_file.read_text(encoding="utf-8"))
        for s_name in ["migrate", "backend", "frontend"]:
            env_files = data["services"][s_name].get("env_file", [])
            # Must be a list with required: false so missing .env doesn't break compose
            assert isinstance(env_files, list)
            assert any(isinstance(item, dict) and item.get("path") == ".env" and item.get("required") is False for item in env_files)
