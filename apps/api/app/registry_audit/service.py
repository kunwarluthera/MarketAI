from datetime import UTC, datetime
from hashlib import sha256
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import RegistryAuditReport
from app.registry_audit.core import replay_lifecycle, verify_event_chain


def persist_audit(session: Session, scope: str, events: list[dict]) -> dict:
    replay = replay_lifecycle(events)
    chain = verify_event_chain(events)
    payload = {"scope": scope, "replay": replay, "chain": chain, "historical_only": True}
    identity = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    if (
        session.scalar(
            select(RegistryAuditReport).where(RegistryAuditReport.report_identity == identity)
        )
        is None
    ):
        session.add(
            RegistryAuditReport(
                report_identity=identity,
                scope=scope,
                replayable=replay["replayable"] and chain["valid"],
                payload=payload,
                findings=replay["findings"] + chain["findings"],
                created_at=datetime.now(UTC),
            )
        )
    return {"report_identity": identity, **payload}
