from __future__ import annotations

import json
import math
import re
import unicodedata
from typing import Any, TypeGuard
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


class JevPromptInjectionBlocked(JevContextBlocked):
    """Raised when prompt injection, role spoofing, or delimiter forgery is detected."""

    pass


class JevAuthorityViolation(JevContextBlocked):
    """Raised when a request or model output attempts to assert authority or override verdicts."""

    pass


class JevResponseValidationError(ValueError):
    """Raised when model response structure, token or probability distribution fails validation."""

    pass


class JevIncompleteDistributionError(JevResponseValidationError):
    """Raised when one or more declared option logprobs are missing from runtime response."""

    pass


# ---------------------------------------------------------------------------
# Authoritative Key Classifications (29_JEV_AI_DATA_CONTRACT.md & 31_GUARDRAILS)
# ---------------------------------------------------------------------------

BLIND_DATA_KEYS = frozenset(
    {
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
    }
)

FORBIDDEN_KEYS = frozenset(
    {
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
        # Arbitrary filesystem paths & ORM/DB session internals
        "filesystem_path",
        "arbitrary_file",
        "orm_session",
        "db_session",
        "_sa_instance_state",
    }
)

ALLOWED_CONTEXT_KEYS = frozenset(
    {
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
    }
)

ALLOWED_TOP_SHAP_KEYS = frozenset(
    {
        "feature_name",
        "name",
        "value",
        "contribution",
        "shap_value",
        "rank",
    }
)

ALLOWED_PROVENANCE_KEYS = frozenset(
    {
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
    }
)

ALLOWED_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "host.docker.internal"})


# ---------------------------------------------------------------------------
# Unicode & Zero-Width Normalization for Security Scanning
# ---------------------------------------------------------------------------

_RE_ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff\u00ad]")


def _normalize_for_security_scan(text: str) -> str:
    """Normalizes Unicode homoglyphs/fullwidth forms (NFKC) and strips zero-width chars."""
    stripped = _RE_ZERO_WIDTH.sub("", text)
    return unicodedata.normalize("NFKC", stripped)


# ---------------------------------------------------------------------------
# Sensitive Data Redaction Patterns
# ---------------------------------------------------------------------------

_RE_BEARER_TOKEN = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9_\-\.]{16,}\b")
_RE_API_KEY = re.compile(r"(?i)\b(?:sk|api|key)[-_][A-Za-z0-9_\-]{16,}\b")
_RE_PASSWORD_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|api_key|apikey|access_token|refresh_token|client_secret)"
    r"(['\"]?\s*[:=]\s*['\"]?)([^\s,;'\"&\}]{3,})(['\"]?)"
)
_RE_DB_CONN_STRING = re.compile(
    r"(?i)\b(?:postgres|postgresql|mysql|mssql|mongodb|redis|sqlite)(?:\+[a-z0-9_]+)?://[^\s'\"]+"
)
_RE_WINDOWS_USER_PATH = re.compile(r"(?i)[a-zA-Z]:\\Users\\[^\s\\'\"]+\\[^\s,'\"]+")
_RE_LINUX_USER_PATH = re.compile(r"(?i)/home/[^\s/'\"]+/[^\s,'\"]+")
_RE_BLIND_TEXT_INJECTION = re.compile(
    r"(?i)\b(" + "|".join(sorted(BLIND_DATA_KEYS)) + r")\s*(?:[:=]\s*[^\s,;]+|\b)"
)

_RE_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
_RE_KEY_SEP = re.compile(r"[-\s./]+")


# ---------------------------------------------------------------------------
# Key Inspection & Traversal
# ---------------------------------------------------------------------------


def _normalize_key_variants(key: Any) -> set[str]:
    """Produces normalized lowercase and snake_case key forms to prevent alias bypasses."""
    raw = str(key).strip()
    if not raw:
        return set()
    lowered = raw.lower()
    snake = _RE_KEY_SEP.sub("_", _RE_CAMEL_BOUNDARY.sub(r"\1_\2", raw)).lower().strip("_")
    variants = {lowered}
    if snake:
        variants.add(snake)
    return variants


def walk_keys(value: Any, _seen: set[int] | None = None) -> set[str]:
    """Recursively traverses dictionaries, lists, and objects to extract all key names.

    Keys are normalized to lower-case and snake_case strings for defensive matching.
    """
    if _seen is None:
        _seen = set()
    obj_id = id(value)
    if obj_id in _seen:
        return set()

    keys: set[str] = set()
    if isinstance(value, dict):
        _seen.add(obj_id)
        for key, child in value.items():
            keys.update(_normalize_key_variants(key))
            keys.update(walk_keys(child, _seen))
    elif isinstance(value, (list, tuple, set, frozenset)):
        _seen.add(obj_id)
        for child in value:
            keys.update(walk_keys(child, _seen))
    else:
        if hasattr(value, "__dict__"):
            _seen.add(obj_id)
            for key, child in value.__dict__.items():
                keys.update(_normalize_key_variants(key))
                if key != "_sa_instance_state":
                    keys.update(walk_keys(child, _seen))
        if hasattr(value, "__slots__"):
            _seen.add(obj_id)
            slots = value.__slots__
            slot_names = [slots] if isinstance(slots, str) else list(slots)
            for slot in slot_names:
                keys.update(_normalize_key_variants(slot))
                if slot != "_sa_instance_state" and hasattr(value, slot):
                    keys.update(walk_keys(getattr(value, slot), _seen))
    return keys


# Alias for backward compatibility
_walk_keys = walk_keys


def check_forbidden_keys(value: Any) -> None:
    """Inspects value recursively and raises appropriate exception if forbidden keys exist."""
    found_keys = walk_keys(value)

    blind_found = found_keys & BLIND_DATA_KEYS
    if blind_found:
        raise JevBlindDataBlocked(f"Forbidden Jev AI blind evaluation keys: {sorted(blind_found)}")

    forbidden_found = found_keys & FORBIDDEN_KEYS
    if forbidden_found:
        raise JevForbiddenKeyError(f"Forbidden Jev AI context keys: {sorted(forbidden_found)}")


def check_blind_data_in_text(text: str) -> None:
    """Scans free-form text strings for embedded blind evaluation markers."""
    if not isinstance(text, str) or not text.strip():
        return
    normalized = _normalize_for_security_scan(text)
    match = _RE_BLIND_TEXT_INJECTION.search(normalized)
    if match:
        raise JevBlindDataBlocked(
            f"Blind evaluation data detected in text content: '{match.group(1)}'"
        )


def _scan_nested_strings(value: Any) -> None:
    """Recursively scans string values and keys for blind data, injection, and authority claims."""
    if isinstance(value, str):
        check_blind_data_in_text(value)
        check_prompt_injection(value)
        check_authority_claims(value)
    elif isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str):
                check_blind_data_in_text(k)
                check_prompt_injection(k)
                check_authority_claims(k)
            _scan_nested_strings(v)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            _scan_nested_strings(item)


def _validate_json_primitives(value: Any) -> None:
    """Ensures nested context structures contain only safe JSON-serializable primitives."""
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            raise JevContextBlocked(
                "Non-finite numeric value (NaN/Inf) is forbidden in Jev AI context"
            )
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise JevContextBlocked(
                    f"Context dictionary keys must be strings, got {type(k).__name__}"
                )
            _validate_json_primitives(v)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _validate_json_primitives(item)
        return
    raise JevContextBlocked(
        f"Unsupported non-primitive or ORM object in Jev AI context: {type(value).__name__}"
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
    sanitized = _RE_PASSWORD_ASSIGNMENT.sub(r"\1\2[REDACTED_SECRET]\4", sanitized)
    sanitized = _RE_DB_CONN_STRING.sub("[REDACTED_DB_CONNECTION]", sanitized)
    sanitized = _RE_WINDOWS_USER_PATH.sub("[REDACTED_PATH]", sanitized)
    sanitized = _RE_LINUX_USER_PATH.sub("[REDACTED_PATH]", sanitized)
    return sanitized


def redact_sensitive_data(value: Any) -> Any:
    """Recursively redacts sensitive strings within nested structures without mutating input."""
    if isinstance(value, str):
        return redact_sensitive_text(value)
    elif isinstance(value, dict):
        return {
            (redact_sensitive_text(k) if isinstance(k, str) else k): redact_sensitive_data(v)
            for k, v in value.items()
        }
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


def _is_valid_number(val: Any) -> TypeGuard[int | float]:
    return (
        not isinstance(val, bool)
        and isinstance(val, (int, float))
        and not math.isnan(val)
        and not math.isinf(val)
    )


def apply_allowlist(payload: dict[str, Any], *, strict: bool = False) -> dict[str, Any]:
    """Projects arbitrary context dictionary through the authoritative Jev AI allowlist.

    - Default-deny: only keys defined in ALLOWED_CONTEXT_KEYS are retained.
    - If strict=True: raises JevAllowlistViolation if unknown keys are encountered.
    - Deeply projects top_shap entries to ALLOWED_TOP_SHAP_KEYS.
    - Deeply projects provenance entries to ALLOWED_PROVENANCE_KEYS.
    - Scans string values for blind data, prompt injection, and authority violations.
    - Preserves input immutability by returning a newly constructed dictionary.
    """
    if not isinstance(payload, dict):
        raise JevContextBlocked(f"Payload must be a dictionary, got {type(payload).__name__}")

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
                        if strict:
                            unknown_shap = set(item.keys()) - ALLOWED_TOP_SHAP_KEYS
                            if unknown_shap:
                                raise JevAllowlistViolation(
                                    f"Unknown top_shap keys: {sorted(unknown_shap)}"
                                )
                        clean_item = {k: v for k, v in item.items() if k in ALLOWED_TOP_SHAP_KEYS}
                        _scan_nested_strings(clean_item)
                        _validate_json_primitives(clean_item)
                        if clean_item:
                            projected_shap.append(clean_item)
                projected["top_shap"] = projected_shap
            else:
                projected["top_shap"] = []

        elif key == "provenance":
            if isinstance(val, dict):
                check_forbidden_keys(val)
                if strict:
                    unknown_prov = set(val.keys()) - ALLOWED_PROVENANCE_KEYS
                    if unknown_prov:
                        raise JevAllowlistViolation(
                            f"Unknown provenance keys: {sorted(unknown_prov)}"
                        )
                clean_prov = {
                    k: str(v)
                    for k, v in val.items()
                    if k in ALLOWED_PROVENANCE_KEYS and v is not None
                }
                _scan_nested_strings(clean_prov)
                projected["provenance"] = clean_prov
            else:
                projected["provenance"] = {}

        elif key == "detector_scores":
            if isinstance(val, dict):
                check_forbidden_keys(val)
                _scan_nested_strings(val)
                projected["detector_scores"] = {
                    str(k): float(v) for k, v in val.items() if _is_valid_number(v)
                }
            else:
                projected["detector_scores"] = {}

        elif key == "view_contributions":
            if isinstance(val, dict):
                check_forbidden_keys(val)
                _scan_nested_strings(val)
                projected["view_contributions"] = {
                    str(k): float(v) for k, v in val.items() if _is_valid_number(v)
                }
            else:
                projected["view_contributions"] = {}

        elif key == "latency_ms":
            if isinstance(val, dict):
                check_forbidden_keys(val)
                _scan_nested_strings(val)
                projected["latency_ms"] = {
                    str(k): float(v) for k, v in val.items() if _is_valid_number(v)
                }
            else:
                projected["latency_ms"] = {}

        elif key == "detector_diagnostics":
            if isinstance(val, dict):
                check_forbidden_keys(val)
                _validate_json_primitives(val)
                _scan_nested_strings(val)
                projected["detector_diagnostics"] = redact_sensitive_data(dict(val))
            else:
                projected["detector_diagnostics"] = {}

        elif key == "warnings":
            if isinstance(val, list):
                clean_warnings: list[str] = []
                for w in val:
                    if w is not None:
                        w_str = str(w)
                        _scan_nested_strings(w_str)
                        clean_warnings.append(redact_sensitive_text(w_str))
                projected["warnings"] = clean_warnings
            else:
                projected["warnings"] = []

        elif key in ("malware_score", "suspicion_score", "threshold"):
            if _is_valid_number(val):
                projected[key] = float(val)

        elif key in ("analysis_id", "request_id", "decision"):
            if isinstance(val, str):
                _scan_nested_strings(val)
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
            f"Jev AI context exceeds configured size limit: "
            f"{len(canonical_json)} > {max_chars} chars"
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
    3. Scans string content for prompt injection, authority claims, and blind data;
    4. If strict=True, validates allowlist adherence (including nested top_shap & provenance);
    5. Validates JSON primitives and enforces canonical JSON size cap.
    """
    if not isinstance(payload, dict):
        raise JevContextBlocked(f"Context must be a dictionary, got {type(payload).__name__}")

    # 1 & 2. Forbidden keys & Blind data check
    check_forbidden_keys(payload)

    # 3. Allowlist validation if strict (top-level and nested structures)
    if strict:
        unknown_keys = set(payload.keys()) - ALLOWED_CONTEXT_KEYS
        if unknown_keys:
            raise JevAllowlistViolation(
                f"Unknown or unauthorized context keys: {sorted(unknown_keys)}"
            )
        top_shap_val = payload.get("top_shap")
        if isinstance(top_shap_val, list):
            for item in top_shap_val:
                if isinstance(item, dict):
                    unknown_shap = set(item.keys()) - ALLOWED_TOP_SHAP_KEYS
                    if unknown_shap:
                        raise JevAllowlistViolation(
                            f"Unknown top_shap keys: {sorted(unknown_shap)}"
                        )
        prov_val = payload.get("provenance")
        if isinstance(prov_val, dict):
            unknown_prov = set(prov_val.keys()) - ALLOWED_PROVENANCE_KEYS
            if unknown_prov:
                raise JevAllowlistViolation(f"Unknown provenance keys: {sorted(unknown_prov)}")

    # 4. Validate JSON primitives (rejects ORM objects, bytes, NaN/Inf) and scan strings
    _validate_json_primitives(payload)
    _scan_nested_strings(payload)

    # 5. Size cap enforcement
    canonical_repr = canonical_json_dumps(payload)
    validate_context_size(canonical_repr, max_chars=max_chars)


def validate_local_endpoint(
    base_url: str, allowed_hosts: set[str] | frozenset[str] | None = None
) -> None:
    """Enforces that runtime endpoint points only to approved local loopback hosts."""
    if not isinstance(base_url, str) or not base_url.strip() or any(c.isspace() for c in base_url):
        raise JevContextBlocked("Jev AI endpoint URL is empty or contains whitespace")
    parsed = urlparse(base_url)
    allowed = ALLOWED_LOCAL_HOSTS if allowed_hosts is None else set(allowed_hosts)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in allowed
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.query)
        or bool(parsed.fragment)
    ):
        raise JevContextBlocked("Jev AI endpoint is not on the approved local host allowlist")


# ---------------------------------------------------------------------------
# Prompt Injection & Authority Boundary Enforcement
# ---------------------------------------------------------------------------

_RE_ROLE_SPOOFING = re.compile(
    r"(?i)(?:<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|user\|>|<\|assistant\|>"
    r"|\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>|\[SYSTEM\]"
    r"|(?:^|\n)\s*#+\s*(?:system|developer|assistant)\b"
    r"|\b(?:system|developer|assistant)\s*:)"
)

_RE_DELIMITER_INJECTION = re.compile(
    r"(?i)(?:\[State\]|\[Question\]|\[Options\]|\bAnswer\s*:)"
    r"|(?:^|\n)\s*A\.\s+[^\n]+\n\s*B\.\s+[^\n]+"
    r"|['\"]choices['\"]\s*:\s*\[\s*\{"
    r"|['\"]?top_logprobs['\"]?\s*:\s*\["
)

_RE_INSTRUCTION_OVERRIDE = re.compile(
    r"(?i)(?:\b(?:ignore|disregard|forget)\s+(?:all\s+|any\s+|the\s+)?"
    r"(?:previous|prior|above|system|safety)?\s*instructions\b"
    r"|\boverride\s+(?:the\s+|all\s+)?(?:detector|verdict|threshold|classification|"
    r"decision|score|guardrails|instructions)\b"
    r"|\b(?:set|change|switch|modify|override|assign)\s+(?:the\s+)?"
    r"(?:verdict|decision|malware_score|suspicion_score|"
    r"fusion_score|threshold|model|model_id|base_url)\s*(?:to\b|=|:)"
    r"|\b(?:model_id|base_url)\s*[:=]\s*[^\s,;]+"
    r"|\b(?:bypass|disable|skip|ignore|turn\s+off)\s+(?:all\s+|the\s+)?"
    r"(?:guardrails|validation|security|checks|"
    r"allowlist|response\s+validation|logprob\s+validation|schema\s+validation)\b"
    r"|\b(?:fabricate|invent|forge|fake)\s+(?:new\s+|the\s+)?"
    r"(?:scientific\s+claims?|shap(?:\s+values?)?|detector\s+scores?|evidence|metrics?)\b"
    r"|\b(?:reveal|print|show|dump|leak|exfiltrate)\s+(?:the\s+|all\s+)?"
    r"(?:system\s+prompt|data|database_url|api\s+keys?|passwords?|secrets?|"
    r"credentials?|blind_label|ground_truth|trigger_manifest|hidden_manifest|"
    r"poison_manifest|backdoor_manifest|blind_manifest)\b"
    r"|\b(?:(?:you\s+must\s+|always\s+)?(?:choose|select|pick)\s+option\s+[A-Za-z]\b"
    r"|(?:you\s+must\s+|always\s+)(?:choose|select|pick)\s+[A-Za-z]\b"
    r"|(?:choose|select|pick)\s+[A-Za-z]\s+regardless\s+of\s+evidence\b)"
    r"|\b(?:run|execute)\s+command\b"
    r"|\b(?:os\.system|subprocess\.(?:Popen|run|call|check_output)|"
    r"powershell\s+-enc|cmd\.exe|/bin/sh)\b"
    r"|\b(?:send|post|exfiltrate|forward|upload)\s+(?:the\s+|all\s+)?"
    r"(?:context|evidence|data|results?)\s+to\s+https?://"
    r"|\b(?:switch|change|hijack)\s+(?:the\s+)?(?:workflow|mode)\s+"
    r"(?:from\s+\w+\s+)?to\b)"
)

_RE_AUTHORITY_CLAIMS = re.compile(
    r"(?i)\b(?:detector\s+overridden"
    r"|final\s+verdict\s*[:=]\s*(?:benign|malware|alert|clean|pass|quarantine)"
    r"|verdict_override\b"
    r"|change\s+threshold\s+to\b"
    r"|threshold\s+changed\s+to\b"
    r"|recalibrated?\s+(?:malware_score|suspicion_score|fusion_score|threshold)\b"
    r"|mutate\s+evidence\b"
    r"|scientific\s+ground\s+truth\s*[:=]"
    r"|authoritative\s+verdict\s*[:=]"
    r"|verified\s+against\s+(?:ground_truth|blind_label|true_label|eval_label)\b"
    r"|(?:trigger_manifest|hidden_manifest|poison_manifest|backdoor_manifest|"
    r"blind_manifest)\s+confirms\b"
    r"|executed\s+(?:the\s+)?(?:binary|sample|specimen)\s+in\s+(?:a\s+)?sandbox\b"
    r"|inspected\s+raw\s+(?:pe|binary)\s+bytes\b"
    r"|queried\s+virustotal\b"
    r"|checked\s+external\s+threat\s+(?:feed|intelligence)\b"
    r"|(?:analyst\s+override|system\s+approval|analyst\s+authorization)\s+"
    r"(?:approved|granted)\b"
    r"|quarantine\s+released\b"
    r"|system\s+action\s+executed\b"
    r"|scientifically\s+certified\s+(?:benign|clean|malware|safe)\b"
    r"|mathematically\s+proven\s+(?:false\s+positive|benign|clean|malware)\b"
    r"|(?:computed\s+new|fabricated?)\s+shap\s+values\b"
    r"|re-?ran\s+m[1-5]\s+detector\b)"
)


def check_prompt_injection(text: str) -> None:
    """Scans untrusted input text for prompt injection, role spoofing, or delimiter forgery.

    Raises:
        JevPromptInjectionBlocked: If adversarial injection patterns are detected.
    """
    if not isinstance(text, str) or not text.strip():
        return

    normalized = _normalize_for_security_scan(text)

    m_role = _RE_ROLE_SPOOFING.search(normalized)
    if m_role:
        raise JevPromptInjectionBlocked(
            f"Role spoofing injection pattern detected: '{m_role.group(0)}'"
        )

    m_delim = _RE_DELIMITER_INJECTION.search(normalized)
    if m_delim:
        raise JevPromptInjectionBlocked(
            f"Prompt section delimiter injection detected: '{m_delim.group(0)}'"
        )

    m_override = _RE_INSTRUCTION_OVERRIDE.search(normalized)
    if m_override:
        raise JevPromptInjectionBlocked(
            f"Instruction override pattern detected: '{m_override.group(0)}'"
        )


def check_authority_claims(text: str) -> None:
    """Detects attempts to claim authority over detector decisions or immutable ground truth.

    Raises:
        JevAuthorityViolation: If authority escalation is detected.
    """
    if not isinstance(text, str) or not text.strip():
        return

    normalized = _normalize_for_security_scan(text)
    m = _RE_AUTHORITY_CLAIMS.search(normalized)
    if m:
        raise JevAuthorityViolation(f"Authority claim detected in content: '{m.group(0)}'")


def enforce_advisory_boundary(obj: Any) -> None:
    """Validates that result objects strictly preserve advisory-only semantics."""
    if hasattr(obj, "advisory_only") and not obj.advisory_only:
        raise JevAuthorityViolation("Object must be advisory_only=True")
    if isinstance(obj, dict) and obj.get("advisory_only") is False:
        raise JevAuthorityViolation("Dictionary payload must be advisory_only=True")


def normalize_option_logprobs(
    logprobs_data: Any,
    expected_options: list[Any] | None = None,
    *,
    allow_incomplete: bool = False,
    option_count: int | None = None,
) -> list[Any]:
    """Normalizes runtime log probabilities over declared option letters with numerical stability.

    Computes:
        p_i = exp(l_i - max(l)) / sum_j exp(l_j - max(l))

    Hard invariants:
    - Never fabricates floor logprobs for missing options (even if allow_incomplete=True).
    - Rejects duplicate option tokens in top_logprobs.
    - Rejects control whitespace (\\n, \\r, \\t), lowercase option tokens, boolean logprobs,
      NaN/Inf, and positive logprobs (> 1e-5).
    """
    from x_sentinel.jev_ai.schemas import DecisionOption, OptionProbability

    if expected_options is None and option_count is not None and option_count >= 2:
        expected_options = [
            DecisionOption(id=f"opt_{i}", label=f"Option {chr(ord('A') + i)}")
            for i in range(option_count)
        ]

    if not expected_options or len(expected_options) < 2 or len(expected_options) > 26:
        count = len(expected_options) if expected_options else 0
        raise JevResponseValidationError(
            f"expected_options must contain 2..26 options; got {count}"
        )

    num_options = len(expected_options)
    declared_letters = [chr(ord("A") + i) for i in range(num_options)]
    declared_set = set(declared_letters)

    def _validate_selected_entry(entry: dict[str, Any]) -> None:
        if "token" in entry and entry["token"] is not None:
            sel_tok = entry["token"]
            if not isinstance(sel_tok, str) or any(ch in sel_tok for ch in ("\n", "\r", "\t")):
                raise JevResponseValidationError(
                    f"Selected decision token contains invalid type or "
                    f"control whitespace: {sel_tok!r}"
                )
        if "logprob" in entry and entry["logprob"] is not None:
            sel_lp = entry["logprob"]
            if (
                isinstance(sel_lp, bool)
                or not isinstance(sel_lp, (int, float))
                or math.isnan(sel_lp)
                or math.isinf(sel_lp)
                or float(sel_lp) > 1e-5
            ):
                raise JevResponseValidationError(
                    f"Invalid selected token logprob in content[0]: {sel_lp!r}"
                )

    # Extract top_logprobs list
    top_list: list[dict[str, Any]] = []
    if isinstance(logprobs_data, dict):
        if "content" in logprobs_data and isinstance(logprobs_data["content"], list):
            content_list = logprobs_data["content"]
            if len(content_list) > 1:
                raise JevResponseValidationError(
                    f"Expected single-token decision logprobs; got {len(content_list)} tokens"
                )
            if len(content_list) == 1 and isinstance(content_list[0], dict):
                _validate_selected_entry(content_list[0])
                top_list = content_list[0].get("top_logprobs", [])
        elif "top_logprobs" in logprobs_data and isinstance(logprobs_data["top_logprobs"], list):
            _validate_selected_entry(logprobs_data)
            top_list = logprobs_data["top_logprobs"]
    elif isinstance(logprobs_data, list):
        if len(logprobs_data) > 0 and isinstance(logprobs_data[0], dict):
            if "top_logprobs" in logprobs_data[0]:
                if len(logprobs_data) > 1:
                    raise JevResponseValidationError(
                        f"Expected single-token decision logprobs; got {len(logprobs_data)} tokens"
                    )
                _validate_selected_entry(logprobs_data[0])
                top_list = logprobs_data[0]["top_logprobs"]
            else:
                top_list = logprobs_data

    if not isinstance(top_list, list) or not top_list:
        raise JevResponseValidationError("Runtime response missing valid top_logprobs entries")

    token_logprobs: dict[str, float] = {}
    for item in top_list:
        if not isinstance(item, dict):
            raise JevResponseValidationError("top_logprobs entry must be a dictionary")

        raw_token_val = item.get("token")
        if not isinstance(raw_token_val, str):
            raise JevResponseValidationError("top_logprobs entry missing string 'token'")

        if any(ch in raw_token_val for ch in ("\n", "\r", "\t")):
            raise JevResponseValidationError(
                f"top_logprobs token contains forbidden control whitespace: {raw_token_val!r}"
            )

        stripped_token = raw_token_val.strip()
        if not stripped_token:
            continue

        # Reject lowercase option letters matching declared options
        if stripped_token != stripped_token.upper() and stripped_token.upper() in declared_set:
            raise JevResponseValidationError(
                f"Lowercase option token '{raw_token_val}' is invalid; "
                f"expected uppercase {declared_letters}"
            )

        raw_lp = item.get("logprob")
        if (
            isinstance(raw_lp, bool)
            or not isinstance(raw_lp, (int, float))
            or math.isnan(raw_lp)
            or math.isinf(raw_lp)
        ):
            raise JevResponseValidationError(
                f"Invalid non-finite or boolean logprob value for "
                f"token '{stripped_token}': {raw_lp!r}"
            )

        lp_float = float(raw_lp)
        if lp_float > 1e-5:
            raise JevResponseValidationError(
                f"Logprob cannot be positive (> 0) for token '{stripped_token}': {lp_float}"
            )
        lp_float = min(lp_float, 0.0)

        if stripped_token in declared_set:
            if stripped_token in token_logprobs:
                raise JevResponseValidationError(
                    f"Duplicate option token '{stripped_token}' found in top_logprobs"
                )
            token_logprobs[stripped_token] = lp_float

    # Verify all declared option letters are present — NEVER fabricate floor logprobs
    missing_letters = [letter for letter in declared_letters if letter not in token_logprobs]
    if missing_letters:
        raise JevIncompleteDistributionError(
            f"Missing logprob for option letters {missing_letters} in runtime top_logprobs "
            f"(allow_incomplete={allow_incomplete} cannot fabricate missing logprobs)"
        )

    # Compute stable softmax
    lps = [token_logprobs[letter] for letter in declared_letters]
    max_lp = max(lps)
    exp_lps = [math.exp(lp - max_lp) for lp in lps]
    denom = sum(exp_lps)

    if denom <= 0.0 or math.isnan(denom) or math.isinf(denom):
        raise JevResponseValidationError(
            "Numerical instability during logprob softmax normalization"
        )

    probabilities = [exp_val / denom for exp_val in exp_lps]
    prob_sum = sum(probabilities)
    if abs(prob_sum - 1.0) > 1e-4:
        raise JevResponseValidationError(
            f"Normalized probabilities sum {prob_sum} deviates from 1.0"
        )

    result: list[OptionProbability] = []
    for i, opt in enumerate(expected_options):
        opt_id = opt.id if hasattr(opt, "id") else opt["id"]
        opt_label = opt.label if hasattr(opt, "label") else opt["label"]
        result.append(
            OptionProbability(
                letter=declared_letters[i],
                option_id=str(opt_id),
                label=str(opt_label),
                logprob=lps[i],
                probability=probabilities[i],
            )
        )
    return result


def calculate_expected_score(
    probabilities: list[Any],
    score_levels: list[float],
) -> float:
    """Calculates expected score E[S] = sum(p_i * s_i) over validated distribution."""
    if len(probabilities) != len(score_levels):
        raise JevResponseValidationError(
            f"Probabilities length ({len(probabilities)}) != "
            f"score_levels length ({len(score_levels)})"
        )

    expected = 0.0
    prob_sum = 0.0
    for p_obj, level in zip(probabilities, score_levels, strict=True):
        if isinstance(level, bool) or not isinstance(level, (int, float)):
            raise JevResponseValidationError(f"Invalid score level type: {level!r}")
        prob = p_obj.probability if hasattr(p_obj, "probability") else float(p_obj)
        if not (0.0 <= prob <= 1.0) or math.isnan(prob) or math.isinf(prob):
            raise JevResponseValidationError(f"Invalid probability value in expectation: {prob}")
        if math.isnan(level) or math.isinf(level):
            raise JevResponseValidationError(f"Invalid score level value in expectation: {level}")
        prob_sum += prob
        expected += prob * float(level)

    if abs(prob_sum - 1.0) > 1e-4:
        raise JevResponseValidationError(
            f"Probabilities in calculate_expected_score do not sum to 1.0 (sum={prob_sum})"
        )

    if math.isnan(expected) or math.isinf(expected):
        raise JevResponseValidationError(f"Computed expected score is non-finite: {expected}")

    min_s = min(score_levels)
    max_s = max(score_levels)
    if expected < min_s - 1e-5 or expected > max_s + 1e-5:
        raise JevResponseValidationError(
            f"Computed expected score {expected} outside bounds [{min_s}, {max_s}]"
        )
    return expected


def _extract_truth_fields(evidence: Any) -> dict[str, Any]:
    """Extracts canonical decision, scores, M1-M5 signals, view_contributions, and top_shap."""
    raw: dict[str, Any] = {}
    if hasattr(evidence, "to_canonical_dict"):
        raw = evidence.to_canonical_dict()
    elif hasattr(evidence, "model_dump"):
        raw = evidence.model_dump(mode="json")
    elif isinstance(evidence, dict):
        raw = evidence
    elif hasattr(evidence, "decision"):
        raw = {
            "analysis_id": getattr(evidence, "analysis_id", None),
            "decision": getattr(evidence, "decision", None),
            "malware_score": getattr(evidence, "malware_score", None),
            "suspicion_score": getattr(
                evidence, "suspicion_score", getattr(evidence, "fusion_score", None)
            ),
            "signals": getattr(evidence, "signals", getattr(evidence, "detector_scores", {})),
            "view_contributions": getattr(evidence, "view_contributions", {}),
            "top_shap": getattr(evidence, "top_shap", []),
        }

    analysis_id = raw.get("analysis_id")
    decision = raw.get("decision")
    malware_score = raw.get("malware_score")
    suspicion_score = (
        raw.get("suspicion_score")
        if raw.get("suspicion_score") is not None
        else raw.get("fusion_score")
    )
    raw_signals = raw.get("detector_scores") or raw.get("signals") or {}
    signals: dict[str, float] = {}
    if isinstance(raw_signals, dict):
        for k, v in raw_signals.items():
            if _is_valid_number(v):
                signals[str(k).upper()] = float(v)

    raw_vc = raw.get("view_contributions") or {}
    view_contributions: dict[str, float] = {}
    if isinstance(raw_vc, dict):
        for k, v in raw_vc.items():
            if _is_valid_number(v):
                view_contributions[str(k)] = float(v)

    raw_shap = raw.get("top_shap") or []
    top_shap: list[tuple[str, float]] = []
    if isinstance(raw_shap, list):
        for item in raw_shap:
            if (
                isinstance(item, dict)
                and "feature_name" in item
                and _is_valid_number(item.get("shap_value"))
            ):
                top_shap.append((str(item["feature_name"]), float(item["shap_value"])))

    return {
        "analysis_id": str(analysis_id).strip() if analysis_id is not None else None,
        "decision": str(decision).strip() if decision is not None else None,
        "malware_score": float(malware_score) if _is_valid_number(malware_score) else None,
        "suspicion_score": float(suspicion_score) if _is_valid_number(suspicion_score) else None,
        "signals": signals,
        "view_contributions": view_contributions,
        "top_shap": top_shap,
    }


def verify_detector_truth_unmodified(original_evidence: Any, workflow_result: Any) -> None:
    """Ensures detector verdict, scores, M1-M5 signals, and SHAP were not modified by AI layer."""
    if original_evidence is None or workflow_result is None:
        return

    # Handle CompareResult with (evidence_a, evidence_b) tuple
    if isinstance(original_evidence, tuple) and len(original_evidence) == 2:
        truth_a = _extract_truth_fields(original_evidence[0])
        truth_b = _extract_truth_fields(original_evidence[1])

        res_base_id = getattr(workflow_result, "baseline_id", None)
        if truth_a["analysis_id"] is not None and res_base_id != truth_a["analysis_id"]:
            raise JevAuthorityViolation(
                f"CompareResult baseline_id mutated: expected {truth_a['analysis_id']}, "
                f"got {res_base_id}"
            )
        res_cand_id = getattr(workflow_result, "candidate_id", None)
        if truth_b["analysis_id"] is not None and res_cand_id != truth_b["analysis_id"]:
            raise JevAuthorityViolation(
                f"CompareResult candidate_id mutated: expected {truth_b['analysis_id']}, "
                f"got {res_cand_id}"
            )

        diff = getattr(workflow_result, "deterministic_diff", None)
        if isinstance(diff, dict):
            if (
                truth_a["decision"] is not None
                and diff.get("baseline_decision") is not None
                and str(diff.get("baseline_decision")) != truth_a["decision"]
            ):
                raise JevAuthorityViolation(
                    f"Baseline decision mutated in CompareResult: "
                    f"{truth_a['decision']} -> {diff.get('baseline_decision')}"
                )
            if (
                truth_b["decision"] is not None
                and diff.get("candidate_decision") is not None
                and str(diff.get("candidate_decision")) != truth_b["decision"]
            ):
                raise JevAuthorityViolation(
                    f"Candidate decision mutated in CompareResult: "
                    f"{truth_b['decision']} -> {diff.get('candidate_decision')}"
                )
            expected_delta = round(
                (truth_b["malware_score"] or 0.0) - (truth_a["malware_score"] or 0.0), 4
            )
            if (
                "delta_malware_score" in diff
                and abs(float(diff["delta_malware_score"]) - expected_delta) > 1e-4
            ):
                raise JevAuthorityViolation(
                    f"CompareResult delta_malware_score mutated: "
                    f"expected {expected_delta}, got {diff['delta_malware_score']}"
                )
            expected_susp_delta = round(
                (truth_b["suspicion_score"] or 0.0) - (truth_a["suspicion_score"] or 0.0), 4
            )
            if (
                "delta_suspicion_score" in diff
                and abs(float(diff["delta_suspicion_score"]) - expected_susp_delta) > 1e-4
            ):
                raise JevAuthorityViolation(
                    f"CompareResult delta_suspicion_score mutated: "
                    f"expected {expected_susp_delta}, got {diff['delta_suspicion_score']}"
                )
            sig_deltas = diff.get("signal_deltas")
            if isinstance(sig_deltas, dict):
                all_sigs = sorted(set(truth_a["signals"].keys()) | set(truth_b["signals"].keys()))
                expected_sig_deltas = {
                    sig: round(
                        truth_b["signals"].get(sig, 0.0) - truth_a["signals"].get(sig, 0.0), 4
                    )
                    for sig in all_sigs
                }
                norm_sig_deltas = {
                    str(k).upper(): float(v) for k, v in sig_deltas.items() if _is_valid_number(v)
                }
                if set(norm_sig_deltas.keys()) != set(expected_sig_deltas.keys()):
                    raise JevAuthorityViolation(
                        "CompareResult signal_deltas keys mutated or fabricated"
                    )
                for sig_k, exp_v in expected_sig_deltas.items():
                    if abs(norm_sig_deltas[sig_k] - exp_v) > 1e-4:
                        raise JevAuthorityViolation(
                            f"CompareResult signal_deltas['{sig_k}'] mutated: "
                            f"expected {exp_v}, got {norm_sig_deltas[sig_k]}"
                        )
        return

    truth = _extract_truth_fields(original_evidence)
    orig_decision = truth["decision"]
    orig_score = truth["malware_score"]
    orig_suspicion = truth["suspicion_score"]
    orig_signals = truth["signals"]
    orig_vc = truth["view_contributions"]
    orig_shap = truth["top_shap"]

    # 1. TriageResult checks
    if (
        hasattr(workflow_result, "detector_verdict")
        and workflow_result.detector_verdict is not None
    ):
        if orig_decision is not None and str(workflow_result.detector_verdict) != orig_decision:
            raise JevAuthorityViolation(
                f"Detector verdict mutation detected: {orig_decision} -> "
                f"{workflow_result.detector_verdict}"
            )

    if (
        hasattr(workflow_result, "detector_malware_score")
        and workflow_result.detector_malware_score is not None
    ):
        if (
            orig_score is not None
            and abs(float(workflow_result.detector_malware_score) - orig_score) > 1e-6
        ):
            raise JevAuthorityViolation(
                f"Detector malware score mutation detected: {orig_score} -> "
                f"{workflow_result.detector_malware_score}"
            )

    # 2. ExplainResult checks (evidence_breakdown)
    breakdown = getattr(workflow_result, "evidence_breakdown", None)
    if isinstance(breakdown, dict) and breakdown:
        if (
            orig_decision is not None
            and breakdown.get("canonical_verdict") is not None
            and str(breakdown["canonical_verdict"]) != orig_decision
        ):
            raise JevAuthorityViolation(
                f"ExplainResult canonical_verdict mutation detected: "
                f"{orig_decision} -> {breakdown['canonical_verdict']}"
            )
        if (
            orig_score is not None
            and breakdown.get("malware_score") is not None
            and abs(float(breakdown["malware_score"]) - orig_score) > 1e-6
        ):
            raise JevAuthorityViolation(
                f"ExplainResult malware_score mutation detected: "
                f"{orig_score} -> {breakdown['malware_score']}"
            )
        if (
            orig_suspicion is not None
            and breakdown.get("suspicion_score") is not None
            and abs(float(breakdown["suspicion_score"]) - orig_suspicion) > 1e-6
        ):
            raise JevAuthorityViolation(
                f"ExplainResult suspicion_score mutation detected: "
                f"{orig_suspicion} -> {breakdown['suspicion_score']}"
            )
        res_scores = breakdown.get("detector_scores")
        if isinstance(res_scores, dict):
            norm_res_scores = {
                str(k).upper(): float(v) for k, v in res_scores.items() if _is_valid_number(v)
            }
            if set(norm_res_scores.keys()) != set(orig_signals.keys()):
                raise JevAuthorityViolation(
                    f"ExplainResult detector_scores keys mutated or invented: "
                    f"expected {sorted(orig_signals.keys())}, got {sorted(norm_res_scores.keys())}"
                )
            for sig_k, sig_v in orig_signals.items():
                if abs(norm_res_scores[sig_k] - sig_v) > 1e-6:
                    raise JevAuthorityViolation(
                        f"ExplainResult detector signal '{sig_k}' mutation detected"
                    )
        res_vc = breakdown.get("view_contributions")
        if isinstance(res_vc, dict) and orig_vc:
            if set(res_vc.keys()) != set(orig_vc.keys()):
                raise JevAuthorityViolation("ExplainResult view_contributions keys mutated")
            for vc_k, vc_v in orig_vc.items():
                if abs(float(res_vc[vc_k]) - vc_v) > 1e-6:
                    raise JevAuthorityViolation(
                        f"ExplainResult view_contributions['{vc_k}'] mutation detected"
                    )
        res_shap = breakdown.get("top_shap")
        if isinstance(res_shap, list) and orig_shap:
            if len(res_shap) > len(orig_shap):
                raise JevAuthorityViolation("ExplainResult top_shap contains invented entries")
            for idx, item in enumerate(res_shap):
                if not isinstance(item, dict):
                    raise JevAuthorityViolation("ExplainResult top_shap entry mutated")
                orig_fname, orig_sval = orig_shap[idx]
                if (
                    str(item.get("feature_name")) != orig_fname
                    or not _is_valid_number(item.get("shap_value"))
                    or abs(float(item["shap_value"]) - orig_sval) > 1e-6
                ):
                    raise JevAuthorityViolation("ExplainResult top_shap values mutated")

    # 3. ReportResult checks (detector_summary)
    det_summary = getattr(workflow_result, "detector_summary", None)
    if isinstance(det_summary, dict) and det_summary:
        if (
            orig_decision is not None
            and det_summary.get("verdict") is not None
            and str(det_summary["verdict"]) != orig_decision
        ):
            raise JevAuthorityViolation(
                f"ReportResult verdict mutation detected: "
                f"{orig_decision} -> {det_summary['verdict']}"
            )
        if (
            orig_score is not None
            and det_summary.get("malware_score") is not None
            and abs(float(det_summary["malware_score"]) - orig_score) > 1e-6
        ):
            raise JevAuthorityViolation(
                f"ReportResult malware_score mutation detected: "
                f"{orig_score} -> {det_summary['malware_score']}"
            )
        if (
            orig_suspicion is not None
            and det_summary.get("suspicion_score") is not None
            and abs(float(det_summary["suspicion_score"]) - orig_suspicion) > 1e-6
        ):
            raise JevAuthorityViolation(
                f"ReportResult suspicion_score mutation detected: "
                f"{orig_suspicion} -> {det_summary['suspicion_score']}"
            )
        rep_signals = det_summary.get("signals")
        if isinstance(rep_signals, dict):
            norm_rep_signals = {
                str(k).upper(): float(v) for k, v in rep_signals.items() if _is_valid_number(v)
            }
            if set(norm_rep_signals.keys()) != set(orig_signals.keys()):
                raise JevAuthorityViolation(
                    f"ReportResult signals keys mutated or invented: "
                    f"expected {sorted(orig_signals.keys())}, got {sorted(norm_rep_signals.keys())}"
                )
            for sig_k, sig_v in orig_signals.items():
                if abs(norm_rep_signals[sig_k] - sig_v) > 1e-6:
                    raise JevAuthorityViolation(
                        f"ReportResult detector signal '{sig_k}' mutation detected"
                    )


# ---------------------------------------------------------------------------
# BE-13 Failure Classification Contract
# ---------------------------------------------------------------------------


def classify_jev_failure(exc: BaseException) -> Any:
    """Maps Jev AI exceptions to canonical BE-13 error codes and DB statuses."""
    from x_sentinel.jev_ai.client import (
        JevAIConfigurationError,
        JevAIConnectionError,
        JevAIDisabledError,
        JevAIHTTPError,
        JevAIResponseError,
        JevAITimeout,
        JevAIUnavailable,
    )
    from x_sentinel.jev_ai.schemas import JevFailureClassification

    msg = redact_sensitive_text(str(exc))

    if isinstance(exc, JevAIDisabledError):
        return JevFailureClassification(
            error_code="XS_AI_DISABLED",
            db_status="blocked",
            http_status=503,
            retryable=False,
            message=msg,
        )
    if isinstance(exc, JevAITimeout):
        return JevFailureClassification(
            error_code="XS_AI_TIMEOUT",
            db_status="failed",
            http_status=504,
            retryable=True,
            message=msg,
        )
    if isinstance(exc, JevContextBlocked):
        return JevFailureClassification(
            error_code="XS_AI_CONTEXT_BLOCKED",
            db_status="blocked",
            http_status=422,
            retryable=False,
            message=msg,
        )
    if isinstance(exc, (JevResponseValidationError, JevAIResponseError)):
        return JevFailureClassification(
            error_code="XS_AI_RESPONSE_INVALID",
            db_status="failed",
            http_status=502,
            retryable=False,
            message=msg,
        )
    if isinstance(
        exc, (JevAIConnectionError, JevAIHTTPError, JevAIUnavailable, JevAIConfigurationError)
    ):
        return JevFailureClassification(
            error_code="XS_AI_UNAVAILABLE",
            db_status="failed",
            http_status=503,
            retryable=isinstance(exc, (JevAIConnectionError, JevAIHTTPError)),
            message=msg,
        )
    return JevFailureClassification(
        error_code="XS_AI_UNAVAILABLE",
        db_status="failed",
        http_status=500,
        retryable=False,
        message=msg,
    )
