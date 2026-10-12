from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from x_sentinel.database.models import AuditEvent


class AuditEventRepository:
    """Append-only repository for durable audit trail events.

    In accordance with SEC-006 and the immutable audit contract,
    historical audit records cannot be modified or deleted through this repository.
    """

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, event_id: int) -> AuditEvent | None:
        return self.session.get(AuditEvent, event_id)

    def get_by_request_id(self, request_id: str) -> Sequence[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.request_id == request_id)
            .order_by(AuditEvent.id)
        )
        return self.session.scalars(stmt).all()

    def get_by_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> Sequence[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.entity_type == entity_type,
                AuditEvent.entity_id == entity_id,
            )
            .order_by(AuditEvent.id)
        )
        return self.session.scalars(stmt).all()

    def add(self, event: AuditEvent) -> AuditEvent:
        """Appends a new audit event to the append-only table."""
        self.session.add(event)
        self.session.flush()
        return event

    def list_recent(self, limit: int = 100, offset: int = 0) -> Sequence[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .order_by(desc(AuditEvent.id))
            .limit(limit)
            .offset(offset)
        )
        return self.session.scalars(stmt).all()
