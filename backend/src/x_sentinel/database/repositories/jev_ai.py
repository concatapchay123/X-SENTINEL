from __future__ import annotations

import json
import math
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from x_sentinel.config import settings
from x_sentinel.database.models import JevAIFeedback, JevAIRun
from x_sentinel.jev_ai.guardrails import (
    JevContextBlocked,
    _validate_json_primitives,
    check_authority_claims,
    check_blind_data_in_text,
    check_forbidden_keys,
    check_prompt_injection,
    redact_sensitive_text,
)

VALID_JEV_MODES: frozenset[str] = frozenset({"explain", "triage", "compare", "report", "docs"})
VALID_JEV_STATUSES: frozenset[str] = frozenset(
    {"queued", "running", "completed", "failed", "blocked"}
)
TERMINAL_JEV_STATUSES: frozenset[str] = frozenset({"completed", "failed", "blocked"})
VALID_FEEDBACK_LABELS: frozenset[str] = frozenset(
    {"helpful", "not_helpful", "incorrect", "unsafe", "unclear"}
)

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MAX_FEEDBACK_COMMENT_LEN = 2000
_MAX_ERROR_MESSAGE_LEN = 2000


class JevAIRepositoryError(ValueError):
    """Base exception for Jev AI repository validation and persistence invariant violations."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class InvalidRunStateTransitionError(JevAIRepositoryError):
    """Raised when attempting an illegal status transition or mutating a terminal JevAIRun."""

    def __init__(self, message: str) -> None:
        super().__init__("XS_INVALID_RUN_TRANSITION", message)


class DuplicateFeedbackError(JevAIRepositoryError):
    """Raised when a user submits duplicate feedback for the same JevAIRun."""

    def __init__(self, message: str) -> None:
        super().__init__("XS_DUPLICATE_FEEDBACK", message)


def _validate_sha256_digest(digest: str, field_name: str) -> str:
    if not isinstance(digest, str):
        raise JevAIRepositoryError(
            "XS_INPUT_INVALID", f"{field_name} must be a 64-character lowercase hex string"
        )
    normalized = digest.strip().lower()
    if normalized.startswith("sha256:"):
        normalized = normalized[7:]
    if not _SHA256_HEX_RE.match(normalized):
        raise JevAIRepositoryError(
            "XS_INPUT_INVALID",
            f"{field_name} must be a valid 64-character hexadecimal SHA-256 digest; got {digest!r}",
        )
    return normalized


_SUPPLEMENTAL_OVERRIDE_RE = re.compile(
    r"(?i)(?:\boverrid(?:e|es|ed|ing)\s+(?:the\s+|all\s+)?"
    r"(?:detector|verdict|threshold|classification|decision|score)\b"
    r"|\bdetector\s+verdict\s+(?:overridden|changed|set)\b)"
)
_WINDOWS_ABS_PATH_RE = re.compile(
    r"(?i)\b[a-zA-Z]:\\(?:[^\s\\/:*?\"<>|]+\\)*[^\s\\/:*?\"<>|.,;'\")]+"
)
_POSIX_ABS_PATH_RE = re.compile(
    r"(?i)(?<!\w)/(?:etc|var|tmp|opt|root|proc|sys|Users|home)/[^\s,'\";\)]+"
)
_BEARER_SUPPLEMENTAL_RE = re.compile(r"(?i)\bBearer\s+(?!\[REDACTED)[A-Za-z0-9._\-~+/]{6,}=*")


def _redact_all_sensitive_text(text: str) -> str:
    redacted = redact_sensitive_text(text)
    redacted = _BEARER_SUPPLEMENTAL_RE.sub("Bearer [REDACTED]", redacted)
    redacted = _WINDOWS_ABS_PATH_RE.sub("[REDACTED_PATH]", redacted)
    redacted = _POSIX_ABS_PATH_RE.sub("[REDACTED_PATH]", redacted)
    return redacted


def _scan_and_redact_nested_strings(value: Any) -> Any:
    if isinstance(value, str):
        check_blind_data_in_text(value)
        check_prompt_injection(value)
        check_authority_claims(value)
        if _SUPPLEMENTAL_OVERRIDE_RE.search(value):
            raise JevAIRepositoryError(
                "XS_AI_CONTEXT_BLOCKED",
                "Authority or detector verdict override claim detected in context_summary",
            )
        return _redact_all_sensitive_text(value)
    if isinstance(value, dict):
        cleaned_dict: dict[str, Any] = {}
        for k, v in value.items():
            if isinstance(k, str):
                check_blind_data_in_text(k)
                check_prompt_injection(k)
                check_authority_claims(k)
            cleaned_dict[str(k)] = _scan_and_redact_nested_strings(v)
        return cleaned_dict
    if isinstance(value, (list, tuple)):
        return [_scan_and_redact_nested_strings(item) for item in value]
    return value


def _validate_safe_context_summary(
    summary: dict[str, Any], max_chars: int | None = None
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        raise JevAIRepositoryError(
            "XS_AI_CONTEXT_BLOCKED", "context_summary must be a JSON object dictionary"
        )
    try:
        _validate_json_primitives(summary)
        check_forbidden_keys(summary)
        redacted_summary = _scan_and_redact_nested_strings(summary)
    except JevContextBlocked as exc:
        raise JevAIRepositoryError("XS_AI_CONTEXT_BLOCKED", str(exc)) from exc

    effective_max = max_chars if max_chars is not None else settings.jev_ai_max_context_chars
    serialized = json.dumps(redacted_summary, ensure_ascii=False, sort_keys=True)
    if len(serialized) > effective_max:
        raise JevAIRepositoryError(
            "XS_AI_CONTEXT_BLOCKED",
            f"context_summary exceeds maximum size of {effective_max} characters "
            f"(got {len(serialized)} characters)",
        )
    return redacted_summary


def _validate_and_sanitize_response_text(response_text: str | None) -> str | None:
    if response_text is None:
        return None
    if not isinstance(response_text, str):
        raise JevAIRepositoryError("XS_INPUT_INVALID", "response_text must be a string")
    cleaned = _CONTROL_CHAR_RE.sub("", response_text)
    try:
        check_blind_data_in_text(cleaned)
        check_authority_claims(cleaned)
    except JevContextBlocked as exc:
        raise JevAIRepositoryError("XS_AI_CONTEXT_BLOCKED", str(exc)) from exc
    if _SUPPLEMENTAL_OVERRIDE_RE.search(cleaned):
        raise JevAIRepositoryError(
            "XS_AI_CONTEXT_BLOCKED",
            "response_text rejected: authority or verdict override claim detected",
        )
    return _redact_all_sensitive_text(cleaned)


def _validate_latency_ms(latency_ms: float | int | None) -> float | None:
    if latency_ms is None:
        return None
    if isinstance(latency_ms, bool) or not isinstance(latency_ms, (int, float)):
        raise JevAIRepositoryError(
            "XS_INPUT_INVALID", "latency_ms must be a finite non-negative number"
        )
    val = float(latency_ms)
    if not math.isfinite(val) or val < 0.0:
        raise JevAIRepositoryError(
            "XS_INPUT_INVALID", "latency_ms must be a finite non-negative number"
        )
    return val


def sanitize_error_message(error_message: str | None) -> str | None:
    """Sanitize and redact sensitive tokens and filesystem paths from persisted error messages."""
    if error_message is None:
        return None
    cleaned = _CONTROL_CHAR_RE.sub("", str(error_message)).strip()
    if not cleaned:
        return None
    redacted = _redact_all_sensitive_text(cleaned)
    if len(redacted) > _MAX_ERROR_MESSAGE_LEN:
        redacted = redacted[: _MAX_ERROR_MESSAGE_LEN - 3] + "..."
    return redacted


def validate_and_sanitize_feedback_comment(comment: str | None) -> str | None:
    """Validate feedback comment against length, control chars, injection, and redact secrets."""
    if comment is None:
        return None
    if not isinstance(comment, str):
        raise JevAIRepositoryError("XS_FEEDBACK_INVALID", "Feedback comment must be a string")
    if _CONTROL_CHAR_RE.search(comment):
        raise JevAIRepositoryError(
            "XS_FEEDBACK_INVALID",
            "Feedback comment contains forbidden control characters or NUL bytes",
        )
    stripped = comment.strip()
    if not stripped:
        return None
    if len(stripped) > _MAX_FEEDBACK_COMMENT_LEN:
        raise JevAIRepositoryError(
            "XS_FEEDBACK_INVALID",
            f"Feedback comment exceeds maximum length of {_MAX_FEEDBACK_COMMENT_LEN} characters",
        )
    try:
        check_blind_data_in_text(stripped)
        check_prompt_injection(stripped)
        check_authority_claims(stripped)
    except JevContextBlocked as exc:
        raise JevAIRepositoryError(
            "XS_FEEDBACK_INVALID",
            f"Feedback comment rejected by safety guardrails: {exc}",
        ) from exc

    if _SUPPLEMENTAL_OVERRIDE_RE.search(stripped):
        raise JevAIRepositoryError(
            "XS_FEEDBACK_INVALID",
            "Feedback comment rejected: authority or verdict override claim detected",
        )

    return _redact_all_sensitive_text(stripped)


class JevAIRunRepository:
    """Repository for persisting, transitioning, and querying JevAIRun audit records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_run(
        self,
        *,
        mode: str,
        status: str,
        model_id: str,
        prompt_version: str,
        input_digest_sha256: str,
        context_summary: dict[str, Any],
        analysis_job_id: uuid.UUID | None = None,
        requested_by_user_id: uuid.UUID | None = None,
        endpoint_label: str = "lm_studio_local",
        output_digest_sha256: str | None = None,
        response_text: str | None = None,
        latency_ms: float | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        completed_at: datetime | None = None,
        run_id: uuid.UUID | None = None,
    ) -> JevAIRun:
        if mode not in VALID_JEV_MODES:
            raise JevAIRepositoryError(
                "XS_INPUT_INVALID",
                f"Invalid Jev AI mode {mode!r}; expected one of {sorted(VALID_JEV_MODES)}",
            )
        if status not in VALID_JEV_STATUSES:
            raise JevAIRepositoryError(
                "XS_INPUT_INVALID",
                f"Invalid Jev AI status {status!r}; expected one of {sorted(VALID_JEV_STATUSES)}",
            )
        if not isinstance(model_id, str) or not model_id.strip():
            raise JevAIRepositoryError("XS_INPUT_INVALID", "model_id must be a non-empty string")
        if not isinstance(prompt_version, str) or not prompt_version.strip():
            raise JevAIRepositoryError(
                "XS_INPUT_INVALID", "prompt_version must be a non-empty string"
            )

        clean_input_digest = _validate_sha256_digest(input_digest_sha256, "input_digest_sha256")
        clean_output_digest = (
            _validate_sha256_digest(output_digest_sha256, "output_digest_sha256")
            if output_digest_sha256 is not None
            else None
        )
        safe_summary = _validate_safe_context_summary(context_summary)
        safe_error_msg = sanitize_error_message(error_message)
        clean_error_code = error_code.strip() if error_code and error_code.strip() else None
        safe_response_text = _validate_and_sanitize_response_text(response_text)
        clean_latency = _validate_latency_ms(latency_ms)

        if status == "completed":
            if clean_output_digest is None:
                raise JevAIRepositoryError(
                    "XS_INPUT_INVALID",
                    "Completed Jev AI run requires a valid 64-character output_digest_sha256",
                )
            if clean_error_code is not None or safe_error_msg is not None:
                raise JevAIRepositoryError(
                    "XS_INPUT_INVALID",
                    "Completed Jev AI run cannot record error_code or error_message",
                )
        elif status in {"failed", "blocked"}:
            if clean_output_digest is not None or safe_response_text is not None:
                raise JevAIRepositoryError(
                    "XS_INPUT_INVALID",
                    (
                        f"Jev AI run with status '{status}' must not store "
                        "response_text or output_digest_sha256"
                    ),
                )

        effective_completed_at = completed_at
        if status in TERMINAL_JEV_STATUSES and effective_completed_at is None:
            effective_completed_at = datetime.now(UTC)

        record = JevAIRun(
            id=run_id or uuid.uuid4(),
            analysis_job_id=analysis_job_id,
            requested_by_user_id=requested_by_user_id,
            mode=mode,
            status=status,
            model_id=model_id.strip(),
            endpoint_label=(endpoint_label or "lm_studio_local").strip(),
            prompt_version=prompt_version.strip(),
            input_digest_sha256=clean_input_digest,
            output_digest_sha256=clean_output_digest,
            context_summary=safe_summary,
            response_text=safe_response_text,
            latency_ms=clean_latency,
            error_code=clean_error_code,
            error_message=safe_error_msg,
            completed_at=effective_completed_at,
        )
        self._session.add(record)
        self._session.flush()
        return record

    def transition_run(
        self,
        *,
        run_id: uuid.UUID,
        status: str,
        output_digest_sha256: str | None = None,
        response_text: str | None = None,
        latency_ms: float | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        context_summary: dict[str, Any] | None = None,
        model_id: str | None = None,
        prompt_version: str | None = None,
        completed_at: datetime | None = None,
    ) -> JevAIRun:
        record = self.get_by_id(run_id)
        if record is None:
            raise JevAIRepositoryError(
                "XS_AI_RUN_NOT_FOUND", f"Jev AI run '{run_id}' does not exist"
            )

        if record.status in TERMINAL_JEV_STATUSES:
            raise InvalidRunStateTransitionError(
                f"Cannot transition Jev AI run '{run_id}' from terminal status "
                f"'{record.status}' to '{status}'"
            )

        if status not in VALID_JEV_STATUSES:
            raise JevAIRepositoryError("XS_INPUT_INVALID", f"Invalid target status {status!r}")

        if record.status == "running" and status == "queued":
            raise InvalidRunStateTransitionError(
                f"Cannot transition Jev AI run '{run_id}' backwards from 'running' to 'queued'"
            )

        if status == "completed":
            effective_out_digest = (
                _validate_sha256_digest(output_digest_sha256, "output_digest_sha256")
                if output_digest_sha256 is not None
                else record.output_digest_sha256
            )
            if effective_out_digest is None:
                raise JevAIRepositoryError(
                    "XS_INPUT_INVALID",
                    "Transition to 'completed' requires a valid 64-character output_digest_sha256",
                )
            if error_code is not None or error_message is not None:
                raise JevAIRepositoryError(
                    "XS_INPUT_INVALID",
                    "Transition to 'completed' cannot set error_code or error_message",
                )
            record.output_digest_sha256 = effective_out_digest
            record.error_code = None
            record.error_message = None
        elif status in {"failed", "blocked"}:
            if output_digest_sha256 is not None or response_text is not None:
                raise JevAIRepositoryError(
                    "XS_INPUT_INVALID",
                    (
                        f"Transition to '{status}' must not store "
                        "response_text or output_digest_sha256"
                    ),
                )
            record.output_digest_sha256 = None
            record.response_text = None
        elif output_digest_sha256 is not None:
            record.output_digest_sha256 = _validate_sha256_digest(
                output_digest_sha256, "output_digest_sha256"
            )

        if context_summary is not None:
            record.context_summary = _validate_safe_context_summary(context_summary)
        if response_text is not None:
            record.response_text = _validate_and_sanitize_response_text(response_text)
        elif status in TERMINAL_JEV_STATUSES and response_text is None:
            record.response_text = None

        if latency_ms is not None:
            record.latency_ms = _validate_latency_ms(latency_ms)
        if error_code is not None:
            record.error_code = error_code.strip() if error_code.strip() else None
        if error_message is not None:
            record.error_message = sanitize_error_message(error_message)
        if model_id is not None and model_id.strip():
            record.model_id = model_id.strip()
        if prompt_version is not None and prompt_version.strip():
            record.prompt_version = prompt_version.strip()

        record.status = status
        if status in TERMINAL_JEV_STATUSES:
            record.completed_at = completed_at or datetime.now(UTC)

        self._session.flush()
        return record

    def get_by_id(self, run_id: uuid.UUID) -> JevAIRun | None:
        return self._session.get(JevAIRun, run_id)

    def list_runs(
        self,
        *,
        analysis_job_id: uuid.UUID | None = None,
        requested_by_user_id: uuid.UUID | None = None,
        mode: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[JevAIRun], int]:
        stmt = select(JevAIRun)
        count_stmt = select(func.count()).select_from(JevAIRun)

        if analysis_job_id is not None:
            stmt = stmt.where(JevAIRun.analysis_job_id == analysis_job_id)
            count_stmt = count_stmt.where(JevAIRun.analysis_job_id == analysis_job_id)
        if requested_by_user_id is not None:
            stmt = stmt.where(JevAIRun.requested_by_user_id == requested_by_user_id)
            count_stmt = count_stmt.where(JevAIRun.requested_by_user_id == requested_by_user_id)
        if mode is not None:
            stmt = stmt.where(JevAIRun.mode == mode)
            count_stmt = count_stmt.where(JevAIRun.mode == mode)
        if status is not None:
            stmt = stmt.where(JevAIRun.status == status)
            count_stmt = count_stmt.where(JevAIRun.status == status)

        total = int(self._session.execute(count_stmt).scalar_one())
        stmt = (
            stmt.order_by(JevAIRun.created_at.desc(), JevAIRun.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(self._session.scalars(stmt).all())
        return items, total


class JevAIFeedbackRepository:
    """Repository for validating, persisting, and listing analyst feedback on Jev AI runs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_feedback(
        self,
        *,
        jev_ai_run_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        rating: int | None = None,
        label: str | None = None,
        comment: str | None = None,
    ) -> JevAIFeedback:
        run = self._session.get(JevAIRun, jev_ai_run_id)
        if run is None:
            raise JevAIRepositoryError(
                "XS_AI_RUN_NOT_FOUND", f"Jev AI run '{jev_ai_run_id}' does not exist"
            )
        if run.status not in TERMINAL_JEV_STATUSES:
            raise JevAIRepositoryError(
                "XS_AI_RUN_NOT_TERMINAL",
                (
                    "Feedback can only be recorded for terminal Jev AI runs; "
                    f"current status is '{run.status}'"
                ),
            )

        if rating is not None:
            if isinstance(rating, bool) or not isinstance(rating, int) or not (1 <= rating <= 5):
                raise JevAIRepositoryError(
                    "XS_FEEDBACK_INVALID",
                    f"Feedback rating must be an integer between 1 and 5; got {rating!r}",
                )

        if label is not None:
            if not isinstance(label, str) or label not in VALID_FEEDBACK_LABELS:
                raise JevAIRepositoryError(
                    "XS_FEEDBACK_INVALID",
                    f"Feedback label must be one of {sorted(VALID_FEEDBACK_LABELS)}; got {label!r}",
                )

        clean_comment = validate_and_sanitize_feedback_comment(comment)

        if rating is None and label is None and clean_comment is None:
            raise JevAIRepositoryError(
                "XS_FEEDBACK_INVALID",
                (
                    "Feedback submission must include at least one of "
                    "rating, label, or non-empty comment"
                ),
            )

        if user_id is not None:
            dup_stmt = select(JevAIFeedback).where(
                JevAIFeedback.jev_ai_run_id == jev_ai_run_id,
                JevAIFeedback.user_id == user_id,
            )
            existing = self._session.scalars(dup_stmt).first()
            if existing is not None:
                raise DuplicateFeedbackError(
                    f"Duplicate feedback already exists for run '{jev_ai_run_id}' "
                    f"and user '{user_id}'"
                )

        feedback = JevAIFeedback(
            id=uuid.uuid4(),
            jev_ai_run_id=jev_ai_run_id,
            user_id=user_id,
            rating=rating,
            label=label,
            comment=clean_comment,
        )
        self._session.add(feedback)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateFeedbackError(
                f"Feedback persistence conflict for run '{jev_ai_run_id}'"
            ) from exc
        return feedback

    def list_for_run(self, jev_ai_run_id: uuid.UUID) -> list[JevAIFeedback]:
        stmt = (
            select(JevAIFeedback)
            .where(JevAIFeedback.jev_ai_run_id == jev_ai_run_id)
            .order_by(JevAIFeedback.created_at.asc(), JevAIFeedback.id.asc())
        )
        return list(self._session.scalars(stmt).all())
