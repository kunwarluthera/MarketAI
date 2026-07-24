from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import (
    ExplainabilityEvent,
    ExplainabilityLineageRecord,
    ExplainabilityManifest,
    ExplainabilityPolicy,
    ExplainabilityProvenance,
    ExplainabilityRequest,
)
from app.prediction_governance.core import checksum

POLICY = "CONTROLLED_EXPLAINABILITY_V1"


def create_request(
    session: Session, prediction_identity: str, requested_by: str, provenance: dict
) -> dict:
    policy = session.scalar(
        select(ExplainabilityPolicy).where(ExplainabilityPolicy.policy_code == POLICY)
    )
    payload = {
        "prediction_identity": prediction_identity,
        "provenance": provenance,
        "policy": POLICY,
    }
    identity = checksum(payload)
    existing = session.scalar(
        select(ExplainabilityRequest).where(ExplainabilityRequest.explainability_id == identity)
    )
    if existing:
        return {"explainability_id": identity, "status": existing.status, "idempotent": True}
    eligibility = (
        "eligible"
        if policy
        and policy.enabled
        and provenance.get("governance_manifest")
        and provenance.get("immutable", True)
        else "ineligible"
    )
    session.add(
        ExplainabilityRequest(
            explainability_id=identity,
            prediction_identity=prediction_identity,
            requested_by=requested_by,
            status="requested",
            eligibility=eligibility,
            payload=payload,
            checksum=checksum(payload),
            created_at=datetime.now(UTC),
        )
    )
    session.add(
        ExplainabilityEvent(
            explainability_id=identity,
            event_identity=checksum({"id": identity, "event": "request_created"}),
            event_type="request_created",
            payload={"eligibility": eligibility},
            created_at=datetime.now(UTC),
        )
    )
    if eligibility == "eligible":
        manifest_payload = {**payload, "algorithm": "placeholder", "explainability_id": identity}
        session.add(
            ExplainabilityProvenance(
                explainability_id=identity,
                payload=provenance,
                checksum=checksum(provenance),
                created_at=datetime.now(UTC),
            )
        )
        session.add(
            ExplainabilityManifest(
                explainability_id=identity,
                payload=manifest_payload,
                checksum=checksum(manifest_payload),
                created_at=datetime.now(UTC),
            )
        )
        session.add(
            ExplainabilityEvent(
                explainability_id=identity,
                event_identity=checksum({"id": identity, "event": "manifest_created"}),
                event_type="manifest_created",
                payload={},
                created_at=datetime.now(UTC),
            )
        )
    return {
        "explainability_id": identity,
        "status": "requested",
        "eligibility": eligibility,
        "idempotent": False,
    }


def lineage_operation(
    session: Session, record_type: str, source_identity: str, payload: dict
) -> dict:
    identity = checksum({"type": record_type, "source": source_identity, "payload": payload})
    if session.scalar(
        select(ExplainabilityLineageRecord).where(
            ExplainabilityLineageRecord.record_identity == identity
        )
    ):
        return {"record_identity": identity, "idempotent": True}
    session.add(
        ExplainabilityLineageRecord(
            record_identity=identity,
            record_type=record_type,
            source_identity=source_identity,
            payload=payload,
            checksum=checksum(payload),
            created_at=datetime.now(UTC),
        )
    )
    return {"record_identity": identity, "idempotent": False}


def replay(session: Session, source_identity: str) -> dict:
    return lineage_operation(session, "replay", source_identity, {"mode": "exact"})


def compare(session: Session, left_identity: str, right_identity: str) -> dict:
    return lineage_operation(
        session, "comparison", left_identity, {"right_identity": right_identity}
    )


def invalidate(session: Session, source_identity: str, reason: str) -> dict:
    if not reason.strip():
        raise ValueError("invalidation_reason_required")
    return lineage_operation(session, "invalidation", source_identity, {"reason": reason})


def supersede(session: Session, source_identity: str, successor_identity: str) -> dict:
    return lineage_operation(
        session, "supersession", source_identity, {"successor_identity": successor_identity}
    )
