from __future__ import annotations

from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.models import (
    OfflinePredictionRecord,
    PredictionValidationEvent,
    PredictionValidationManifest,
    PredictionValidationPolicy,
    PredictionValidationRequest,
    PredictionValidationResult,
    ModelLoadManifest,
)
from app.prediction_validation.core import checksum, execute_rules

POLICY_CODE = "CONTROLLED_PREDICTION_VALIDATION_V1"


def request_validation(
    session: Session, prediction_identity: str, requested_by: str, reason: str
) -> dict:
    session.scalar(
        select(PredictionValidationPolicy).where(
            PredictionValidationPolicy.validation_policy_code == POLICY_CODE,
            PredictionValidationPolicy.enabled.is_(True),
        )
    )
    request_identity = checksum({"prediction": prediction_identity, "policy": POLICY_CODE})
    existing = session.scalar(
        select(PredictionValidationRequest).where(
            PredictionValidationRequest.request_identity == request_identity
        )
    )
    if existing:
        return {"request_identity": existing.request_identity, "status": existing.request_status}
    row = PredictionValidationRequest(
        request_identity=request_identity,
        prediction_result_identity=prediction_identity,
        validation_policy=POLICY_CODE,
        requested_by=requested_by,
        request_reason=reason,
        request_status="requested",
        created_at=datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    session.add(
        PredictionValidationEvent(
            event_identity=checksum({"request": request_identity, "event": "validation_requested"}),
            request_identity=request_identity,
            event_type="validation_requested",
            payload={"prediction_identity": prediction_identity},
            created_at=datetime.now(UTC),
        )
    )
    return {"request_identity": request_identity, "status": "requested"}


def execute_validation(session: Session, request_identity: str) -> dict:
    request = session.scalar(
        select(PredictionValidationRequest).where(
            PredictionValidationRequest.request_identity == request_identity
        )
    )
    if request is None:
        raise ValueError("Validation request not found")
    session.add(
        PredictionValidationEvent(
            event_identity=checksum({"request": request_identity, "event": "validation_started"}),
            request_identity=request_identity,
            event_type="validation_started",
            payload={},
            created_at=datetime.now(UTC),
        )
    )
    prediction = session.scalar(
        select(OfflinePredictionRecord).where(
            OfflinePredictionRecord.prediction_identity == request.prediction_result_identity
        )
    )
    policy_row = session.scalar(
        select(PredictionValidationPolicy).where(
            PredictionValidationPolicy.validation_policy_code == request.validation_policy
        )
    )
    prediction_payload = prediction.payload if prediction else None
    policy = {"enabled": policy_row.enabled} if policy_row else None
    manifest_row = None
    if prediction is not None:
        manifest_row = session.scalar(
            select(ModelLoadManifest)
            .where(ModelLoadManifest.version_identity == prediction.model_version)
            .order_by(ModelLoadManifest.created_at.desc())
        )
    manifest = prediction_payload.get("manifest") if prediction_payload else None
    if manifest is None and manifest_row is not None:
        manifest = {
            "load_identity": manifest_row.load_identity,
            "status": manifest_row.status,
            "checksum_valid": manifest_row.status == "loaded",
        }
    outcomes = execute_rules(prediction_payload, policy, manifest)
    passed = all(item["passed"] for item in outcomes)
    decision = "validated" if passed else "validation_failed"
    eligibility = "eligible" if passed else "ineligible"
    result = PredictionValidationResult(
        request_identity=request_identity,
        decision=decision,
        eligibility=eligibility,
        rule_outcomes=outcomes,
        created_at=datetime.now(UTC),
    )
    session.add(result)
    payload = {
        "request_identity": request_identity,
        "prediction_identity": request.prediction_result_identity,
        "policy": request.validation_policy,
        "rules": outcomes,
        "decision": decision,
    }
    digest = checksum(payload)
    manifest_row = PredictionValidationManifest(
        manifest_identity=checksum({"request": request_identity}),
        request_identity=request_identity,
        prediction_identity=request.prediction_result_identity,
        payload=payload,
        manifest_checksum=digest,
        created_at=datetime.now(UTC),
    )
    session.add(manifest_row)
    request.request_status = "completed"
    session.add(
        PredictionValidationEvent(
            event_identity=checksum({"request": request_identity, "event": "manifest_created"}),
            request_identity=request_identity,
            event_type="manifest_created",
            payload={"manifest_checksum": digest},
            created_at=datetime.now(UTC),
        )
    )
    final_event = "validation_completed" if passed else "validation_failed"
    session.add(
        PredictionValidationEvent(
            event_identity=checksum({"request": request_identity, "event": final_event}),
            request_identity=request_identity,
            event_type=final_event,
            payload={"decision": decision},
            created_at=datetime.now(UTC),
        )
    )
    return {**payload, "manifest_checksum": digest}
