from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Patterns matching confirmed production credentials
SECRET_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "PRIVATE_KEY",
        "P0_CRITICAL",
        re.compile(r"-----BEGIN (?:[A-Z0-9_-]+\s+)?PRIVATE KEY-----", re.MULTILINE),
    ),
    (
        "AWS_KEY",
        "P0_CRITICAL",
        re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"),
    ),
    (
        "GCP_API_KEY",
        "P0_CRITICAL",
        re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"),
    ),
    (
        "DB_CONNECTION_PASSWORD",
        "P0_CRITICAL",
        re.compile(
            r"(?:postgres|mysql|mssql(?:\+pyodbc)?|mongodb(?:\+srv)?):\/\/(?P<user>[^:\s\/]+):(?P<password>[^\s'\"]{6,}?)@(?:[a-zA-Z0-9_\-\.]+|localhost)",
            re.IGNORECASE,
        ),
    ),
    (
        "HARDCODED_JWT_SECRET",
        "P1_HIGH",
        re.compile(
            r"(?:jwt_secret|signing_key|secret_key)\s*[:=]\s*['\"](?P<secret>[A-Za-z0-9_\-\.+=]{16,})['\"]",
            re.IGNORECASE,
        ),
    ),
    (
        "PASSWORD_ASSIGNMENT",
        "P1_HIGH",
        re.compile(
            r"(?:password|passwd|pwd)\s*[:=]\s*['\"](?P<secret>[^'\"\s]{8,})['\"]",
            re.IGNORECASE,
        ),
    ),
]

# Whitelist / False positive substrings and synthetic fixtures
SYNTHETIC_WHITELIST_TOKENS: frozenset[str] = frozenset(
    {
        "token-admin",
        "token-analyst",
        "token-evaluator",
        "token-operator",
        "token-analyst-2",
        "token-inactive",
        "trusted_connection=yes",
        "placeholder",
        "password_placeholder",
        "change_me",
        "your-secret-here",
        "test-token",
        "synthetic",
        "dummy",
        "example",
        "cistrongpassword2025!",
        "xsentinel_strong_pass_2025!",
        "supersecretpass123!",
        "supersecret123!",
        "supersecretpassword123!",
        "p@ssw0rd99",
        "00000000-0000-0000-0000-000000000001",
        "11111111-1111-1111-1111-111111111111",
    }
)

SENSITIVE_KEY_NAMES: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "api_key",
        "private_key",
        "signing_key",
        "jwt_secret",
        "authorization",
        "credentials",
        "auth_token",
    }
)


@dataclass(frozen=True)
class SecretFinding:
    """Detailed metadata for a detected secret finding."""

    file_path: str
    line_number: int
    secret_type: str
    severity: str
    masked_snippet: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "secret_type": self.secret_type,
            "severity": self.severity,
            "masked_snippet": self.masked_snippet,
        }


def mask_secret(text: str, visible_prefix: int = 4, visible_suffix: int = 2) -> str:
    """Masks secret text leaving minimal context."""
    stripped = text.strip()
    if len(stripped) <= visible_prefix + visible_suffix:
        return "***REDACTED***"
    return f"{stripped[:visible_prefix]}***REDACTED***{stripped[-visible_suffix:]}"


def is_synthetic_whitelist(snippet: str) -> bool:
    """Identifies test fixture tokens or documentation placeholders."""
    lower = snippet.lower()
    return any(token in lower for token in SYNTHETIC_WHITELIST_TOKENS)


def scan_text_for_secrets(
    text: str,
    file_path: str = "<memory>",
    ignore_synthetic: bool = True,
) -> list[SecretFinding]:
    """Scans string content line-by-line for credentials matching classified patterns."""
    findings: list[SecretFinding] = []
    lines = text.splitlines()

    for idx, line in enumerate(lines, start=1):
        for sec_type, severity, pattern in SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                matched_str = match.group(0)
                if ignore_synthetic and (
                    is_synthetic_whitelist(matched_str) or is_synthetic_whitelist(line)
                ):
                    continue
                snippet = line.replace(matched_str, mask_secret(matched_str)).strip()
                findings.append(
                    SecretFinding(
                        file_path=file_path,
                        line_number=idx,
                        secret_type=sec_type,
                        severity=severity,
                        masked_snippet=snippet,
                    )
                )
    return findings


def scan_file_for_secrets(
    path: Path,
    ignore_synthetic: bool = True,
) -> list[SecretFinding]:
    """Scans a single file on disk."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    return scan_text_for_secrets(
        content, file_path=str(path.as_posix()), ignore_synthetic=ignore_synthetic
    )


def scan_directory_for_secrets(
    root: Path,
    exclude_dirs: tuple[str, ...] = (
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "node_modules",
        ".venv",
        "venv",
        ".gemini",
    ),
    allowed_extensions: tuple[str, ...] = (
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
    ignore_synthetic: bool = True,
) -> list[SecretFinding]:
    """Scans a repository directory tree for leaked secrets."""
    findings: list[SecretFinding] = []
    if not root.exists():
        return findings

    for item in root.rglob("*"):
        if item.is_file():
            # Check exclusions
            if any(part in item.parts for part in exclude_dirs):
                continue
            if item.suffix.lower() not in allowed_extensions and item.name not in {
                ".env",
                ".env.example",
            }:
                continue
            findings.extend(scan_file_for_secrets(item, ignore_synthetic=ignore_synthetic))
    return findings


def redact_sensitive_text(text: str) -> str:
    """Sanitizes text by replacing credential patterns with [REDACTED]."""
    redacted = text
    for _, _, pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def redact_sensitive_dict(data: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively redacts dictionary values associated with sensitive keys or matching patterns."""
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        key_str = str(key).strip().lower()
        if key_str in SENSITIVE_KEY_NAMES:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, Mapping):
            sanitized[key] = redact_sensitive_dict(value)
        elif isinstance(value, (list, tuple)):
            sanitized[key] = [
                redact_sensitive_dict(v) if isinstance(v, Mapping) else v for v in value
            ]
        elif isinstance(value, str):
            sanitized[key] = redact_sensitive_text(value)
        else:
            sanitized[key] = value
    return sanitized


def assert_no_secrets_in_diagnostics(payload: Mapping[str, Any]) -> None:
    """Raises ValueError if any unredacted sensitive keys are present in diagnostic output."""
    for key, val in payload.items():
        key_lower = str(key).lower().strip()
        if key_lower in SENSITIVE_KEY_NAMES and val != "[REDACTED]":
            raise ValueError(f"Diagnostic payload contains unredacted sensitive key: '{key}'")
        if isinstance(val, Mapping):
            assert_no_secrets_in_diagnostics(val)
