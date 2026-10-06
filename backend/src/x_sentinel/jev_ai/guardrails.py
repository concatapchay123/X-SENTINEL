from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

FORBIDDEN_KEYS = {
    "blind_label",
    "ground_truth",
    "trigger_manifest",
    "hidden_manifest",
    "raw_pe",
    "raw_binary",
    "api_key",
    "password",
    "database_url",
}

ALLOWED_LOCAL_HOSTS = {"localhost", "127.0.0.1", "host.docker.internal"}


class JevContextBlocked(ValueError):
    pass


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key).lower())
            keys.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_walk_keys(child))
    return keys


def validate_context(payload: dict[str, Any], max_chars: int = 30_000) -> None:
    found = _walk_keys(payload) & FORBIDDEN_KEYS
    if found:
        raise JevContextBlocked(f"Forbidden Jev AI context keys: {sorted(found)}")
    if len(str(payload)) > max_chars:
        raise JevContextBlocked("Jev AI context exceeds configured size limit")


def validate_local_endpoint(base_url: str, allowed_hosts: set[str] | None = None) -> None:
    parsed = urlparse(base_url)
    allowed = ALLOWED_LOCAL_HOSTS if allowed_hosts is None else allowed_hosts
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in allowed:
        raise JevContextBlocked("Jev AI endpoint is not on the approved local host allowlist")
