from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.common.models import AuditLog


def append(
    session: Session,
    event_type: str,
    entity_type: str,
    entity_id: str,
    metadata: dict,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    actor: str = "local-user",
) -> AuditLog:
    event = AuditLog(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor=actor,
        occurred_at=datetime.now(UTC),
        correlation_id=correlation_id or str(uuid4()),
        causation_id=causation_id,
        metadata_json=metadata,
    )
    session.add(event)
    return event
