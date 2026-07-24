from __future__ import annotations

from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.models import (
    ConfidenceEvidence,
    OfflinePredictionRecord,
    PredictionValidationResult,
    StatisticalValidationPolicy,
    StatisticalValidationRequest,
    StatisticalValidationResult,
    StatisticalValidationEvent,
    StatisticalValidationManifest,
    StatisticalValidationLifecycle,
    StatisticalValidationReplay,
)
from app.prediction_validation.core import checksum
from app.statistical_validation.core import (
    StatisticalPolicy,
    classification_statistics,
    statistical_decision,
)

POLICY_CODE = "CONTROLLED_STATISTICAL_PREDICTION_VALIDATION_V1"


def replay_request(session: Session, request_identity: str, replay_payload: dict) -> dict:
    """Persist an immutable, idempotent comparison against the request manifest."""
    manifest = session.scalar(
        select(StatisticalValidationManifest).where(
            StatisticalValidationManifest.request_identity == request_identity
        )
    )
    if manifest is None:
        raise ValueError("Statistical validation manifest not found")
    expected = manifest.payload
    keys = sorted(set(expected) | set(replay_payload))
    mismatches = [key for key in keys if expected.get(key) != replay_payload.get(key)]
    status = "matched" if not mismatches else "mismatched"
    replay_identity = checksum(
        {
            "request": request_identity,
            "manifest": manifest.manifest_identity,
            "payload": replay_payload,
        }
    )
    existing = session.scalar(
        select(StatisticalValidationReplay).where(
            StatisticalValidationReplay.replay_identity == replay_identity
        )
    )
    if existing:
        return {
            "replay_identity": existing.replay_identity,
            "request_identity": existing.request_identity,
            "manifest_identity": existing.manifest_identity,
            "status": existing.status,
            "mismatches": existing.mismatches,
            "replay_checksum": existing.replay_checksum,
        }
    result = {
        "request_identity": request_identity,
        "manifest_identity": manifest.manifest_identity,
        "status": status,
        "mismatches": mismatches,
    }
    replay_checksum = checksum(result)
    session.add(
        StatisticalValidationReplay(
            replay_identity=replay_identity,
            request_identity=request_identity,
            manifest_identity=manifest.manifest_identity,
            status=status,
            mismatches=mismatches,
            replay_checksum=replay_checksum,
            created_at=datetime.now(UTC),
        )
    )
    session.add(
        StatisticalValidationEvent(
            event_identity=checksum({"replay": replay_identity}),
            request_identity=request_identity,
            event_type="statistical_validation_replayed",
            payload={"replay_identity": replay_identity, "status": status},
            created_at=datetime.now(UTC),
        )
    )
    return {"replay_identity": replay_identity, **result, "replay_checksum": replay_checksum}


def replay_history(session: Session, request_identity: str) -> list[dict]:
    rows = session.scalars(
        select(StatisticalValidationReplay)
        .where(StatisticalValidationReplay.request_identity == request_identity)
        .order_by(StatisticalValidationReplay.created_at)
    ).all()
    return [
        {
            "replay_identity": row.replay_identity,
            "manifest_identity": row.manifest_identity,
            "status": row.status,
            "mismatches": row.mismatches,
            "replay_checksum": row.replay_checksum,
        }
        for row in rows
    ]


def record_lifecycle(
    session: Session, request_identity: str, action: str, reason: str, actor_identity: str
) -> dict:
    if action not in {"invalidate", "supersede"}:
        raise ValueError("Unsupported lifecycle action")
    identity = checksum({"request": request_identity, "action": action, "reason": reason})
    existing = session.scalar(
        select(StatisticalValidationLifecycle).where(
            StatisticalValidationLifecycle.lifecycle_identity == identity
        )
    )
    if existing:
        return {"lifecycle_identity": identity, "action": existing.action}
    session.add(
        StatisticalValidationLifecycle(
            lifecycle_identity=identity,
            request_identity=request_identity,
            action=action,
            reason=reason,
            actor_identity=actor_identity,
            payload={"request_identity": request_identity, "action": action, "reason": reason},
            created_at=datetime.now(UTC),
        )
    )
    session.add(
        StatisticalValidationEvent(
            event_identity=checksum({"lifecycle": identity}),
            request_identity=request_identity,
            event_type=f"statistical_{action}",
            payload={"lifecycle_identity": identity, "reason": reason},
            created_at=datetime.now(UTC),
        )
    )
    return {"lifecycle_identity": identity, "action": action}


def create_request(
    session: Session, parent_request_identity: str, prediction_identity: str
) -> dict:
    identity = checksum(
        {
            "parent": parent_request_identity,
            "prediction": prediction_identity,
            "policy": POLICY_CODE,
        }
    )
    existing = session.scalar(
        select(StatisticalValidationRequest).where(
            StatisticalValidationRequest.request_identity == identity
        )
    )
    if existing:
        return {"request_identity": existing.request_identity, "status": existing.status}
    row = StatisticalValidationRequest(
        request_identity=identity,
        parent_validation_request_identity=parent_request_identity,
        prediction_result_identity=prediction_identity,
        policy_code=POLICY_CODE,
        status="requested",
        request_checksum=identity,
        created_at=datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    return {"request_identity": identity, "status": row.status}


def execute_request(session: Session, request_identity: str) -> dict:
    request = session.scalar(
        select(StatisticalValidationRequest).where(
            StatisticalValidationRequest.request_identity == request_identity
        )
    )
    if request is None:
        raise ValueError("Statistical validation request not found")
    existing = session.scalar(
        select(StatisticalValidationResult).where(
            StatisticalValidationResult.request_identity == request_identity
        )
    )
    if existing:
        return {
            "request_identity": request_identity,
            "decision": existing.decision,
            "result_checksum": existing.result_checksum,
        }
    session.add(
        StatisticalValidationEvent(
            event_identity=checksum(
                {"request": request_identity, "event": "statistical_validation_started"}
            ),
            request_identity=request_identity,
            event_type="statistical_validation_started",
            payload={},
            created_at=datetime.now(UTC),
        )
    )
    parent = session.scalar(
        select(PredictionValidationResult).where(
            PredictionValidationResult.request_identity
            == request.parent_validation_request_identity
        )
    )
    prediction = session.scalar(
        select(OfflinePredictionRecord).where(
            OfflinePredictionRecord.prediction_identity == request.prediction_result_identity
        )
    )
    policy_row = session.scalar(
        select(StatisticalValidationPolicy).where(
            StatisticalValidationPolicy.policy_code == request.policy_code
        )
    )
    if parent is None or parent.decision != "validated":
        request.status = "eligibility_failed"
        return {"request_identity": request_identity, "decision": "structural_validation_required"}
    if prediction is None or policy_row is None or not policy_row.enabled:
        request.status = "eligibility_failed"
        return {"request_identity": request_identity, "decision": "incomplete"}
    payload = prediction.payload
    classes = payload.get("classes")
    probabilities = payload.get("probabilities")
    if not isinstance(classes, list) or not isinstance(probabilities, list):
        request.status = "eligibility_failed"
        return {
            "request_identity": request_identity,
            "decision": "validation_failed",
            "reason": "probability_missing",
        }
    configured = policy_row.payload
    stats = classification_statistics(
        classes,
        probabilities,
        StatisticalPolicy(
            minimum_confidence=float(configured.get("minimum_confidence", 0.5)),
            maximum_entropy=float(configured.get("maximum_entropy", 1.0)),
            probability_tolerance=float(configured.get("probability_tolerance", 1e-9)),
        ),
    )
    evidence_payload = {"prediction_identity": prediction.prediction_identity, **stats}
    evidence_checksum = checksum(evidence_payload)
    session.add(
        ConfidenceEvidence(
            evidence_identity=evidence_checksum,
            prediction_result_identity=prediction.prediction_identity,
            payload=evidence_payload,
            evidence_checksum=evidence_checksum,
            created_at=datetime.now(UTC),
        )
    )
    decision = statistical_decision(stats)
    result_payload = {"stats": stats, "decision": decision}
    result_checksum = checksum(result_payload)
    session.add(
        StatisticalValidationResult(
            request_identity=request_identity,
            decision=decision["decision"],
            rule_results=[stats],
            result_checksum=result_checksum,
            created_at=datetime.now(UTC),
        )
    )
    manifest_checksum = checksum({"request_identity": request_identity, **result_payload})
    session.add(
        StatisticalValidationManifest(
            manifest_identity=manifest_checksum,
            request_identity=request_identity,
            payload=result_payload,
            manifest_checksum=manifest_checksum,
            created_at=datetime.now(UTC),
        )
    )
    session.add(
        StatisticalValidationEvent(
            event_identity=checksum(
                {"request": request_identity, "event": "statistical_manifest_created"}
            ),
            request_identity=request_identity,
            event_type="statistical_manifest_created",
            payload={"manifest_checksum": manifest_checksum},
            created_at=datetime.now(UTC),
        )
    )
    session.add(
        StatisticalValidationEvent(
            event_identity=checksum(
                {"request": request_identity, "event": "statistical_validation_completed"}
            ),
            request_identity=request_identity,
            event_type="statistical_validation_completed",
            payload={"decision": decision["decision"]},
            created_at=datetime.now(UTC),
        )
    )
    request.status = "completed"
    return {
        "request_identity": request_identity,
        **result_payload,
        "result_checksum": result_checksum,
    }
