from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.attribution.core import checksum
from app.common.models import (
    RuntimeOperationPolicy,
    RuntimeHealthSnapshot,
    RuntimeReport,
    RuntimeOperationalRecord,
)


def snapshot(session: Session, metrics: dict) -> dict:
    policy = session.scalar(
        select(RuntimeOperationPolicy).where(
            RuntimeOperationPolicy.policy_code == "CONTROLLED_RUNTIME_OPERATIONS_V1"
        )
    )
    if policy is None or not policy.enabled:
        raise ValueError("policy_disabled")
    digest = checksum({"policy": policy.policy_code, "metrics": metrics})
    if session.scalar(
        select(RuntimeHealthSnapshot).where(RuntimeHealthSnapshot.snapshot_checksum == digest)
    ):
        return {"snapshot_checksum": digest, "idempotent": True}
    session.add(
        RuntimeHealthSnapshot(
            snapshot_checksum=digest,
            payload={"policy": policy.policy_code, "metrics": metrics},
            created_at=datetime.now(UTC),
        )
    )
    return {"snapshot_checksum": digest, "idempotent": False}


def report(session: Session, payload: dict) -> dict:
    digest = checksum(payload)
    if session.scalar(select(RuntimeReport).where(RuntimeReport.report_checksum == digest)):
        return {"report_checksum": digest, "idempotent": True}
    session.add(
        RuntimeReport(report_checksum=digest, payload=payload, created_at=datetime.now(UTC))
    )
    return {"report_checksum": digest, "idempotent": False}


def operational_record(session: Session, record_type: str, payload: dict) -> dict:
    digest = checksum({"type": record_type, "payload": payload})
    if session.scalar(
        select(RuntimeOperationalRecord).where(RuntimeOperationalRecord.record_identity == digest)
    ):
        return {"record_identity": digest, "idempotent": True}
    session.add(
        RuntimeOperationalRecord(
            record_identity=digest,
            record_type=record_type,
            payload=payload,
            checksum=digest,
            created_at=datetime.now(UTC),
        )
    )
    return {"record_identity": digest, "idempotent": False}
