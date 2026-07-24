from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import ExplainabilityGovernance, ExplainabilityGovernanceRecord
from app.attribution.core import checksum

TRANSITIONS = {
    "pending": {"approved", "rejected", "published", "revoked", "superseded"},
    "approved": {"published", "revoked", "superseded"},
    "published": {"revoked", "superseded"},
}


def record(session: Session, artifact_id: str, record_type: str, payload: dict) -> dict:
    digest = checksum({"artifact": artifact_id, "type": record_type, "payload": payload})
    if session.scalar(
        select(ExplainabilityGovernanceRecord).where(
            ExplainabilityGovernanceRecord.checksum == digest
        )
    ):
        return {"checksum": digest, "idempotent": True}
    session.add(
        ExplainabilityGovernanceRecord(
            artifact_id=artifact_id,
            record_type=record_type,
            payload=payload,
            checksum=digest,
            created_at=datetime.now(UTC),
        )
    )
    return {"checksum": digest, "idempotent": False}


def transition(session: Session, artifact_id: str, target: str, payload: dict) -> dict:
    row = session.scalar(
        select(ExplainabilityGovernance).where(ExplainabilityGovernance.artifact_id == artifact_id)
    )
    if row is None:
        row = ExplainabilityGovernance(
            artifact_id=artifact_id,
            status="pending",
            payload=payload,
            checksum=checksum(payload),
            created_at=datetime.now(UTC),
        )
        session.add(row)
    if target not in TRANSITIONS.get(row.status, set()):
        raise ValueError("invalid_governance_transition")
    result = record(session, artifact_id, target, payload)
    row.status = target
    return {"artifact_id": artifact_id, "status": target, **result}


def validate_replay(session: Session, artifact_id: str, expected_checksum: str) -> dict:
    row = session.scalar(
        select(ExplainabilityGovernance).where(ExplainabilityGovernance.artifact_id == artifact_id)
    )
    verified = bool(row and row.checksum == expected_checksum)
    return {
        "artifact_id": artifact_id,
        "verified": verified,
        **record(
            session,
            artifact_id,
            "replay_verified",
            {"expected_checksum": expected_checksum, "verified": verified},
        ),
    }
