from __future__ import annotations

import json
import math
import re
from typing import Any
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Exception Hierarchy
# ---------------------------------------------------------------------------


class JevContextBlocked(ValueError):
    """Base exception raised when Jev AI context violates safety contracts."""

    pass


class JevForbiddenKeyError(JevContextBlocked):
    """Raised when context contains explicitly forbidden schema keys."""

    pass


class JevBlindDataBlocked(JevForbiddenKeyError):
    """Raised when blind evaluation ground truth or hidden manifests are detected."""

    pass


class JevContextSizeExceeded(JevContextBlocked):
    """Raised when serialized context exceeds configured size cap."""

    pass


class JevAllowlistViolation(JevContextBlocked):
    """Raised when context contains unrecognized or non-allowlisted keys in strict mode."""

    pass


# ---------------------------------------------------------------------------
# Authoritative Key Classifications (29_JEV_AI_DATA_CONTRACT.md & 31_GUARDRAILS)
# ---------------------------------------------------------------------------

BLIND_DATA_KEYS = frozenset({
    "blind_label",
    "ground_truth",
    "true_label",
    "eval_label",
    "target_label",
    "blind_ground_truth",
    "hidden_label",
    "trigger_manifest",
    "hidden_manifest",
    "poison_manifest",
    "backdoor_manifest",
    "blind_manifest",
})

FORBIDDEN_KEYS = frozenset({
    # Raw binary / PE execution data
    "raw_pe",
    "raw_binary",
    "raw_bytes",
    "pe_bytes",
    "file_bytes",
    "binary_data",
    "byte_stream",
    # Full unaggregated feature vector (2,381 features)
    "features",
    "feature_vector",
    "raw_features",
    "vector",
    "full_vector",
    "raw_vector",
    "feature_array",
    # Secrets, credentials, authentication material
    "api_key",
    "secret",
    "password",
    "passwd",
    "pwd",
    "token",
    "auth_token",
    "access_token",
    "database_url",
    "db_password",
    "private_key",
    "client_secret",
    # Blind evaluation & ground truth
    "blind_label",
    "ground_truth",
    "true_label",
    "eval_label",
    "target_label",
    "blind_ground_truth",
    "hidden_label",
    # Trigger / backdoor manifests
    "trigger_manifest",
    "hidden_manifest",
    "poison_manifest",
    "backdoor_manifest",
    "blind_manifest",
    # PII & user data
    "user_data",
    "personal_data",
    "pii",
    "credit_card",
    "ssn",
    # Arbitrary filesystem paths
    "filesystem_path",
    "arbitrary_file",
})

ALLOWED_CONTEXT_KEYS = frozenset({
    "analysis_id",
    "request_id",
    "decision",
    "malware_score",
    "suspicion_score",
    "threshold",
    "detector_scores",
    "detector_diagnostics",
    "view_contributions",
    "top_shap",
    "provenance",
    "warnings",
    "latency_ms",
})

ALLOWED_TOP_SHAP_KEYS = frozenset({
    "feature_name",
    "name",
    "value",
    "contribution",
    "shap_value",
    "rank",
})

ALLOWED_PROVENANCE_KEYS = frozenset({
    "model_hash",
    "model_config_hash",
    "view_map_hash",
    "detector_config_hash",
    "build_digest",
    "code_commit",
    "timestamp",
    "seed",
    "threshold_id",
    "demo_mode",
})

ALLOWED_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "host.docker.internal"})


# ---------------------------------------------------------------------------
# Sensitive Data Redaction Patterns
# ---------------------------------------------------------------------------

_RE_BEARER_TOKEN = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9_\-\.]{16,}\b")
_RE_API_KEY = re.compile(r"(?i)\b(?:sk|api|key)[-_][A-Za-z0-9_\-]{16,}\b")
_RE_PASSWORD_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|pwd|secret)\s*[:=]\s*['\"]?([^\s,;'\"&]{3,})['\"]?"
)
_RE_DB_CONN_STRING = re.compile(
    r"(?i)\b(?:postgres|postgresql|mysql|mssql|mongodb|redis|sqlite)://[^\s'\"]+"
)
_RE_WINDOWS_USER_PATH = re.compile(r"(?i)[a-zA-Z]:\\Users\\[^\s\\'\"]+\\[^\s,'\"]+")
_RE_LINUX_USER_PATH = re.compile(r"(?i)/home/[^\s/'\"]+/[^\s,'\"]+")
_RE_BLIND_TEXT_INJECTION = re.compile(
    r"(?i)\b(blind_label|ground_truth|hidden_manifest|trigger_manifest|blind_manifest)\s*[:=]\s*[^\s,;]+"
)


# ---------------------------------------------------------------------------
# Key Inspection & Traversal
# ---------------------------------------------------------------------------


def walk_keys(value: Any) -> set[str]:
    """Recursively traverses dictionaries, lists, and objects to extract all key names.

    Keys are normalized to lower-case stripped strings for defensive matching.
    """
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key).strip().lower())
            keys.update(walk_keys(child))
    elif isinstance(value, (list, tuple, set, frozenset)):
        for child in value:
            keys.update(walk_keys(child))
    elif hasattr(value, "__dict__"):
        for key, child in value.__dict__.items():
            keys.add(str(key).strip().lower())
            keys.update(walk_keys(child))
    return keys


# Alias for backward compatibility
_walk_keys = walk_keys


def check_forbidden_keys(value: Any) -> None:
    """Inspects value recursively and raises appropriate exception if forbidden keys exist."""
    found_keys = walk_keys(value)

    blind_found = found_keys & BLIND_DATA_KEYS
    if blind_found:
        raise JevBlindDataBlocked(
            f"Forbidden Jev AI blind evaluation keys: {sorted(blind_found)}"
        )

    forbidden_found = found_keys & FORBIDDEN_KEYS
    if forbidden_found:
        raise JevForbiddenKeyError(
            f"Forbidden Jev AI context keys: {sorted(forbidden_found)}"
        )


def check_blind_data_in_text(text: str) -> None:
    """Scans free-form text strings for embedded blind evaluation markers."""
    if not isinstance(text, str) or not text.strip():
        return
    match = _RE_BLIND_TEXT_INJECTION.search(text)
    if match:
        raise JevBlindDataBlocked(
            f"Blind evaluation data detected in text content: '{match.group(1)}'"
        )


# ---------------------------------------------------------------------------
# Sensitive Data Redaction
# ---------------------------------------------------------------------------


def redact_sensitive_text(text: str) -> str:
    """Applies deterministic regex redaction to strings containing credentials or private paths."""
    if not isinstance(text, str):
        return text

    sanitized = _RE_BEARER_TOKEN.sub(r"\1[REDACTED_TOKEN]", text)
    sanitized = _RE_API_KEY.sub("[REDACTED_API_KEY]", sanitized)
    sanitized = _RE_PASSWORD_ASSIGNMENT.sub(r"\1=[REDACTED_SECRET]", sanitized)
    sanitized = _RE_DB_CONN_STRING.sub("[REDACTED_DB_CONNECTION]", sanitized)
    sanitized = _RE_WINDOWS_USER_PATH.sub("[REDACTED_PATH]", sanitized)
    sanitized = _RE_LINUX_USER_PATH.sub("[REDACTED_PATH]", sanitized)
    return sanitized


def redact_sensitive_data(value: Any) -> Any:
    """Recursively redacts sensitive strings within nested structures without mutating input."""
    if isinstance(value, str):
        return redact_sensitive_text(value)
    elif isinstance(value, dict):
        return {k: redact_sensitive_data(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    elif isinstance(value, tuple):
        return tuple(redact_sensitive_data(item) for item in value)
    elif isinstance(value, set):
        return {redact_sensitive_data(item) for item in value}
    return value


# ---------------------------------------------------------------------------
# Authoritative Allowlist Projection
# ---------------------------------------------------------------------------


def apply_allowlist(payload: dict[str, Any], *, strict: bool = False) -> dict[str, Any]:
    """Projects arbitrary context dictionary through the authoritative Jev AI allowlist.

    - Default-deny: only keys defined in ALLOWED_CONTEXT_KEYS are retained.
    - If strict=True: raises JevAllowlistViolation if unknown keys are encountered.
    - Deeply projects top_shap entries to ALLOWED_TOP_SHAP_KEYS.
    - Deeply projects provenance entries to ALLOWED_PROVENANCE_KEYS.
    - Preserves input immutability by returning a newly constructed dictionary.
    """
    if not isinstance(payload, dict):
        raise JevContextBlocked(
            f"Payload must be a dictionary, got {type(payload).__name__}"
        )

    # First check for forbidden or blind keys before any projection
    check_forbidden_keys(payload)

    # Validate unknown keys if strict
    if strict:
        unknown_keys = set(payload.keys()) - ALLOWED_CONTEXT_KEYS
        if unknown_keys:
            raise JevAllowlistViolation(
                f"Unknown or unauthorized context keys: {sorted(unknown_keys)}"
            )

    projected: dict[str, Any] = {}

    for key, val in payload.items():
        if key not in ALLOWED_CONTEXT_KEYS or val is None:
            continue

        if key == "top_shap":
            if isinstance(val, list):
                projected_shap: list[dict[str, Any]] = []
                for item in val:
                    if isinstance(item, dict):
                        check_forbidden_keys(item)
                        clean_item = {
                            k: v for k, v in item.items() if k in ALLOWED_TOP_SHAP_KEYS
                        }
                        if clean_item:
                            projected_shap.append(clean_item)
                projected["top_shap"] = projected_shap
            else:
                projected["top_shap"] = []

        elif key == "provenance":
            if isinstance(val, dict):
                check_forbidden_keys(val)
                projected["provenance"] = {
                    k: str(v) for k, v in val.items() if k in ALLOWED_PROVENANCE_KEYS
                }
            else:
                projected["provenance"] = {}

        elif key == "detector_scores":
            if isinstance(val, dict):
                check_forbidden_keys(val)
                projected["detector_scores"] = {
                    str(k): float(v)
                    for k, v in val.items()
                    if isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v)
                }
            else:
                projected["detector_scores"] = {}

        elif key == "view_contributions":
            if isinstance(val, dict):
                check_forbidden_keys(val)
                projected["view_contributions"] = {
                    str(k): float(v)
                    for k, v in val.items()
                    if isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v)
                }
            else:
                projected["view_contributions"] = {}

        elif key == "latency_ms":
            if isinstance(val, dict):
                check_forbidden_keys(val)
                projected["latency_ms"] = {
                    str(k): float(v)
                    for k, v in val.items()
                    if isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v)
                }
            else:
                projected["latency_ms"] = {}

        elif key == "detector_diagnostics":
            if isinstance(val, dict):
                check_forbidden_keys(val)
                # Keep safe primitive diagnostic structures
                projected["detector_diagnostics"] = redact_sensitive_data(dict(val))
            else:
                projected["detector_diagnostics"] = {}

        elif key == "warnings":
            if isinstance(val, list):
                projected["warnings"] = [
                    redact_sensitive_text(str(w)) for w in val if w is not None
                ]
            else:
                projected["warnings"] = []

        elif key in ("malware_score", "suspicion_score", "threshold"):
            if isinstance(val, (int, float)) and not math.isnan(val) and not math.isinf(val):
                projected[key] = float(val)

        elif key in ("analysis_id", "request_id", "decision"):
            if isinstance(val, str):
                projected[key] = val.strip()

    return projected


# ---------------------------------------------------------------------------
# Deterministic Serialization & Digest
# ---------------------------------------------------------------------------


def canonical_json_dumps(payload: Any) -> str:
    """Produces deterministic RFC 8785 compatible JSON serialization."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_context_digest(payload: Any) -> str:
    """Computes standard SHA-256 digest over canonical JSON representation."""
    import hashlib

    canonical_str = canonical_json_dumps(payload)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Validation Gateways
# ---------------------------------------------------------------------------


def validate_context_size(canonical_json: str, max_chars: int = 30_000) -> None:
    """Enforces strict size ceiling over serialized context representation."""
    if len(canonical_json) > max_chars:
        raise JevContextSizeExceeded(
            f"Jev AI context exceeds configured size limit: {len(canonical_json)} > {max_chars} chars"
        )


def validate_context(
    payload: dict[str, Any],
    max_chars: int = 30_000,
    *,
    strict: bool = False,
) -> None:
    """Validates that a context payload adheres to all Jev AI safety contracts:

    1. Scans for forbidden keys (including raw PE, vectors, secrets);
    2. Scans for blind evaluation ground truth or hidden manifests;
    3. If strict=True, validates allowlist adherence;
    4. Serializes to canonical JSON and enforces size cap.
    """
    if not isinstance(payload, dict):
        raise JevContextBlocked(
            f"Context must be a dictionary, got {type(payload).__name__}"
        )

    # 1 & 2. Forbidden keys & Blind data check
    check_forbidden_keys(payload)

    # 3. Allowlist validation if strict
    if strict:
        unknown_keys = set(payload.keys()) - ALLOWED_CONTEXT_KEYS
        if unknown_keys:
            raise JevAllowlistViolation(
                f"Unknown or unauthorized context keys: {sorted(unknown_keys)}"
            )

    # 4. Size cap enforcement
    canonical_repr = canonical_json_dumps(payload)
    validate_context_size(canonical_repr, max_chars=max_chars)


def validate_local_endpoint(base_url: str, allowed_hosts: set[str] | None = None) -> None:
    """Enforces that runtime endpoint points only to approved local loopback hosts."""
    parsed = urlparse(base_url)
    allowed = ALLOWED_LOCAL_HOSTS if allowed_hosts is None else set(allowed_hosts)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in allowed:
        raise JevContextBlocked(
            "Jev AI endpoint is not on the approved local host allowlist"
        )
