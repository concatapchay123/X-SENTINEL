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
        # Arbitrary filesystem paths
        "filesystem_path",
        "arbitrary_file",
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
        raise JevBlindDataBlocked(f"Forbidden Jev AI blind evaluation keys: {sorted(blind_found)}")

    forbidden_found = found_keys & FORBIDDEN_KEYS
    if forbidden_found:
        raise JevForbiddenKeyError(f"Forbidden Jev AI context keys: {sorted(forbidden_found)}")


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
                        clean_item = {k: v for k, v in item.items() if k in ALLOWED_TOP_SHAP_KEYS}
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
    3. If strict=True, validates allowlist adherence;
    4. Serializes to canonical JSON and enforces size cap.
    """
    if not isinstance(payload, dict):
        raise JevContextBlocked(f"Context must be a dictionary, got {type(payload).__name__}")

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
        raise JevContextBlocked("Jev AI endpoint is not on the approved local host allowlist")


# ---------------------------------------------------------------------------
# Prompt Injection & Authority Boundary Enforcement
# ---------------------------------------------------------------------------

_RE_ROLE_SPOOFING = re.compile(
    r"(?i)(?:<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|user\|>|<\|assistant\|>|\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>|\[SYSTEM\]|\b(?:system|developer|assistant)\s*:)"
)

_RE_DELIMITER_INJECTION = re.compile(r"(?i)(?:\[State\]|\[Question\]|\[Options\]|\bAnswer\s*:)")

_RE_INSTRUCTION_OVERRIDE = re.compile(
    r"(?i)\b(?:(?:ignore|disregard|forget)\s+(?:all\s+)?previous\s+instructions"
    r"|override\s+(?:the\s+)?(?:detector|verdict|threshold|classification|decision)"
    r"|set\s+(?:the\s+)?verdict\s+to\b"
    r"|bypass\s+(?:all\s+)?guardrails"
    r"|reveal\s+(?:the\s+)?system\s+prompt"
    r"|exfiltrate\s+(?:the\s+)?data"
    r"|(?:you\s+must\s+|always\s+)?choose\s+option\s+[A-Za-z]\b"
    r"|you\s+must\s+select\s+option\s+[A-Za-z]\b)"
)

_RE_AUTHORITY_CLAIMS = re.compile(
    r"(?i)\b(?:detector\s+overridden"
    r"|final\s+verdict\s*[:=]\s*(?:benign|malware|alert|clean)"
    r"|verdict_override\b"
    r"|change\s+threshold\s+to\b"
    r"|mutate\s+evidence\b"
    r"|scientific\s+ground\s+truth\s*[:=]"
    r"|authoritative\s+verdict\s*[:=])"
)


def check_prompt_injection(text: str) -> None:
    """Scans untrusted input text for prompt injection, role spoofing, or delimiter forgery.

    Raises:
        JevPromptInjectionBlocked: If adversarial injection patterns are detected.
    """
    if not isinstance(text, str) or not text.strip():
        return

    m_role = _RE_ROLE_SPOOFING.search(text)
    if m_role:
        raise JevPromptInjectionBlocked(
            f"Role spoofing injection pattern detected: '{m_role.group(0)}'"
        )

    m_delim = _RE_DELIMITER_INJECTION.search(text)
    if m_delim:
        raise JevPromptInjectionBlocked(
            f"Prompt section delimiter injection detected: '{m_delim.group(0)}'"
        )

    m_override = _RE_INSTRUCTION_OVERRIDE.search(text)
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

    m = _RE_AUTHORITY_CLAIMS.search(text)
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
    expected_options: list[Any],
    *,
    allow_incomplete: bool = False,
) -> list[Any]:
    """Normalizes runtime log probabilities over declared option letters with numerical stability.

    Computes:
        p_i = exp(l_i - max(l)) / sum_j exp(l_j - max(l))

    Args:
        logprobs_data: Raw logprobs structure from OpenAI-compatible runtime.
        expected_options: Declared options list.
        allow_incomplete: Whether to tolerate missing option tokens. Default False.

    Returns:
        list[OptionProbability]: Validated probability distribution.

    Raises:
        JevIncompleteDistributionError: When declared option letter is missing from top_logprobs.
        JevResponseValidationError: When probabilities deviate or encounter numerical invalidity.
    """
    from x_sentinel.jev_ai.schemas import OptionProbability

    # Extract top_logprobs list
    top_list: list[dict[str, Any]] = []
    if isinstance(logprobs_data, dict):
        if "content" in logprobs_data and isinstance(logprobs_data["content"], list):
            if len(logprobs_data["content"]) > 0 and isinstance(logprobs_data["content"][0], dict):
                top_list = logprobs_data["content"][0].get("top_logprobs", [])
        elif "top_logprobs" in logprobs_data and isinstance(logprobs_data["top_logprobs"], list):
            top_list = logprobs_data["top_logprobs"]
    elif isinstance(logprobs_data, list):
        if len(logprobs_data) > 0 and isinstance(logprobs_data[0], dict):
            if "top_logprobs" in logprobs_data[0]:
                top_list = logprobs_data[0]["top_logprobs"]
            else:
                top_list = logprobs_data

    if not isinstance(top_list, list) or not top_list:
        raise JevResponseValidationError("Runtime response missing valid top_logprobs entries")

    token_logprobs: dict[str, float] = {}
    for item in top_list:
        if not isinstance(item, dict):
            continue
        raw_token = str(item.get("token", "")).strip().upper()
        raw_lp = item.get("logprob")
        if not isinstance(raw_lp, (int, float)) or math.isnan(raw_lp) or math.isinf(raw_lp):
            continue
        # If token was previously seen, take maximum logprob
        if raw_token:
            if raw_token not in token_logprobs or float(raw_lp) > token_logprobs[raw_token]:
                token_logprobs[raw_token] = float(raw_lp)

    # Verify all declared option letters are present
    num_options = len(expected_options)
    declared_letters = [chr(ord("A") + i) for i in range(num_options)]

    missing_letters = [letter for letter in declared_letters if letter not in token_logprobs]
    if missing_letters:
        if not allow_incomplete:
            raise JevIncompleteDistributionError(
                f"Missing logprob for option letters {missing_letters} in runtime top_logprobs"
            )
        # Incomplete distribution fallback policy: set unrepresented options to floor logprob
        min_lp = min(token_logprobs.values()) if token_logprobs else -50.0
        floor_lp = min_lp - 10.0
        for missing in missing_letters:
            token_logprobs[missing] = floor_lp

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
    for p_obj, level in zip(probabilities, score_levels, strict=True):
        prob = p_obj.probability if hasattr(p_obj, "probability") else float(p_obj)
        if not (0.0 <= prob <= 1.0) or math.isnan(prob) or math.isinf(prob):
            raise JevResponseValidationError(f"Invalid probability value in expectation: {prob}")
        if math.isnan(level) or math.isinf(level):
            raise JevResponseValidationError(f"Invalid score level value in expectation: {level}")
        expected += prob * level

    if math.isnan(expected) or math.isinf(expected):
        raise JevResponseValidationError(f"Computed expected score is non-finite: {expected}")
    return expected


def verify_detector_truth_unmodified(original_evidence: Any, workflow_result: Any) -> None:
    """Ensures detector verdict, malware score, and M1-M5 signals were not modified by AI layer."""
    if original_evidence is None or workflow_result is None:
        return

    # Extract original values
    orig_dict: dict[str, Any] = {}
    if hasattr(original_evidence, "to_canonical_dict"):
        orig_dict = original_evidence.to_canonical_dict()
    elif isinstance(original_evidence, dict):
        orig_dict = original_evidence
    elif hasattr(original_evidence, "decision"):
        orig_dict = {
            "decision": getattr(original_evidence, "decision", None),
            "malware_score": getattr(original_evidence, "malware_score", None),
        }

    orig_decision = orig_dict.get("decision")
    orig_score = orig_dict.get("malware_score")

    # Check against workflow result
    if (
        hasattr(workflow_result, "detector_verdict")
        and workflow_result.detector_verdict is not None
    ):
        if orig_decision is not None and str(workflow_result.detector_verdict) != str(
            orig_decision
        ):
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
            and abs(float(workflow_result.detector_malware_score) - float(orig_score)) > 1e-6
        ):
            raise JevAuthorityViolation(
                f"Detector malware score mutation detected: {orig_score} -> "
                f"{workflow_result.detector_malware_score}"
            )
