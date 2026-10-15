from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from x_sentinel.security.secrets import redact_sensitive_dict

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from x_sentinel.security.auth import AuthUser

logger = logging.getLogger("x_sentinel.security.audit")


def record_security_event(
    session: Session | None,
    *,
    event_type: str,
    user: AuthUser | None = None,
    user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
    outcome: str = "denied",
) -> None:
    """Records a durable, sanitized security audit event in the database and audit logger.

    Guarantees that credentials, raw auth tokens, and blind labels are redacted before writing.
    """
    actor_id: uuid.UUID | None = None
    if user is not None:
        actor_id = user.user_id
    elif user_id is not None:
        actor_id = user_id

    raw_payload = dict(details or {})
    raw_payload["outcome"] = outcome
    if user is not None:
        raw_payload["roles"] = list(user.roles)

    sanitized_payload = redact_sensitive_dict(raw_payload)

    # Log to Python security logger
    logger.warning(
        "SECURITY EVENT: type=%s actor=%s entity=%s:%s outcome=%s details=%s",
        event_type,
        actor_id,
        entity_type,
        entity_id,
        outcome,
        sanitized_payload,
    )

    if session is not None:
        try:
            from x_sentinel.database.models import AuditEvent

            event = AuditEvent(
                request_id=str(sanitized_payload.get("request_id", "")) or None,
                user_id=actor_id,
                event_type=f"security.{event_type}",
                entity_type=entity_type,
                entity_id=entity_id,
                payload=sanitized_payload,
            )
            session.add(event)
            session.flush()
        except Exception as exc:
            logger.error("Failed to persist security audit event: %s", exc)
