from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.attribution.core import checksum
from app.common.models import EvaluationPolicy, EvaluationRequest, EvaluationRecord


def create_request(session: Session, dataset_id: str, model_id: str, lineage: dict) -> dict:
    policy = session.scalar(
        select(EvaluationPolicy).where(EvaluationPolicy.policy_code == "CONTROLLED_EVALUATION_V1")
    )
    if policy is None or not policy.enabled:
        raise ValueError("policy_disabled")
    if lineage.get("mutable") or lineage.get("is_live"):
        raise ValueError("mutable_dataset_rejected")
    payload = {
        "dataset_id": dataset_id,
        "model_id": model_id,
        "lineage": lineage,
        "policy": policy.policy_code,
    }
    identity = checksum(payload)
    existing = session.scalar(
        select(EvaluationRequest).where(EvaluationRequest.evaluation_id == identity)
    )
    if existing:
        return {"evaluation_id": identity, "status": existing.status, "idempotent": True}
    session.add(
        EvaluationRequest(
            evaluation_id=identity,
            dataset_id=dataset_id,
            model_id=model_id,
            payload=payload,
            checksum=identity,
            created_at=datetime.now(UTC),
        )
    )
    record(session, identity, "request_created", payload)
    return {"evaluation_id": identity, "status": "requested", "idempotent": False}


def record(session: Session, evaluation_id: str, record_type: str, payload: dict) -> dict:
    digest = checksum({"evaluation": evaluation_id, "type": record_type, "payload": payload})
    if session.scalar(select(EvaluationRecord).where(EvaluationRecord.checksum == digest)):
        return {"checksum": digest, "idempotent": True}
    session.add(
        EvaluationRecord(
            evaluation_id=evaluation_id,
            record_type=record_type,
            payload=payload,
            checksum=digest,
            created_at=datetime.now(UTC),
        )
    )
    return {"checksum": digest, "idempotent": False}


def lifecycle(session: Session, evaluation_id: str, record_type: str, payload: dict) -> dict:
    return record(session, evaluation_id, record_type, payload)
