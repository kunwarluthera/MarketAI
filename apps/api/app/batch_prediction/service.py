from __future__ import annotations

from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.batch_prediction.core import checksum, ordered_members
from app.prediction_governance.service import persist_governance
from app.prediction_safety.service import persist_safety_result
from app.prediction_validation.service import execute_validation, request_validation
from app.model_loading.core import LoadPolicy, load_callable_handle
from app.model_loading.service import HandleStore
from app.offline_prediction.core import PredictionPolicy
from app.offline_prediction.service import persist_prediction
from app.common.models import (
    BatchPredictionEvent,
    BatchPredictionItem,
    BatchPredictionManifest,
    BatchPredictionPolicy,
    BatchPredictionRequest,
    BatchPredictionPartition,
    BatchPredictionCheckpoint,
    BatchPredictionCancellation,
    BatchPredictionWorkerLease,
    BatchPredictionReplay,
    BatchPredictionAttempt,
)


def create_batch(session: Session, body: dict, requested_by: str) -> dict:
    request_checksum = checksum(body)
    existing = session.scalar(
        select(BatchPredictionRequest).where(
            BatchPredictionRequest.idempotency_key == body["idempotency_key"]
        )
    )
    if existing:
        if existing.request_checksum != request_checksum:
            raise ValueError("idempotency_conflict")
        return {"batch_id": existing.batch_id, "status": existing.status, "idempotent": True}
    policy = session.scalar(
        select(BatchPredictionPolicy).where(
            BatchPredictionPolicy.policy_code
            == body.get("policy_code", "CONTROLLED_OFFLINE_BATCH_PREDICTION_V1")
        )
    )
    if policy is None or not policy.enabled:
        raise ValueError("policy_disabled")
    members = ordered_members(body.get("universe", {}))
    limits = policy.payload or {}
    if len(members) > int(limits.get("maximum_batch_items", 500)):
        raise ValueError("batch_limit_exceeded")
    batch_id = checksum({"request": request_checksum, "requested_by": requested_by})
    as_of = datetime.fromisoformat(body["as_of_timestamp"].replace("Z", "+00:00"))
    if as_of.tzinfo is None:
        raise ValueError("invalid_as_of_timestamp")
    request = BatchPredictionRequest(
        batch_id=batch_id,
        idempotency_key=body["idempotency_key"],
        requested_by=requested_by,
        policy_code=policy.policy_code,
        universe_type=body.get("universe_type", "explicit_prediction_inputs"),
        universe={"members": members},
        as_of_timestamp=as_of,
        status="materialized",
        request_checksum=request_checksum,
        created_at=datetime.now(UTC),
    )
    session.add(request)
    for ordinal, member in enumerate(members):
        session.add(
            BatchPredictionItem(
                batch_id=batch_id,
                ordinal=ordinal,
                item_key=checksum({"batch": batch_id, "ordinal": ordinal, "member": member}),
                payload=member,
                created_at=datetime.now(UTC),
            )
        )
    event_payload = {
        "batch_id": batch_id,
        "item_count": len(members),
        "request_checksum": request_checksum,
    }
    session.add(
        BatchPredictionEvent(
            batch_id=batch_id,
            event_identity=checksum({"batch": batch_id, "event": "materialized"}),
            event_type="materialized",
            payload=event_payload,
            created_at=datetime.now(UTC),
        )
    )
    manifest_payload = {
        "batch_id": batch_id,
        "policy_code": policy.policy_code,
        "members": members,
        "request_checksum": request_checksum,
    }
    session.add(
        BatchPredictionManifest(
            batch_id=batch_id,
            payload=manifest_payload,
            checksum=checksum(manifest_payload),
            created_at=datetime.now(UTC),
        )
    )
    return {
        "batch_id": batch_id,
        "status": "materialized",
        "item_count": len(members),
        "idempotent": False,
    }


def record_attempt(
    session: Session,
    item_key: str,
    attempt_number: int,
    stage: str,
    outcome: str,
    failure_code: str | None = None,
    retryable: bool = False,
) -> dict:
    if attempt_number < 1:
        raise ValueError("invalid_attempt_number")
    digest = checksum(
        {
            "item": item_key,
            "attempt": attempt_number,
            "stage": stage,
            "outcome": outcome,
            "failure": failure_code,
        }
    )
    existing = session.scalar(
        select(BatchPredictionAttempt).where(BatchPredictionAttempt.attempt_checksum == digest)
    )
    if existing:
        return {
            "attempt_checksum": digest,
            "attempt_number": existing.attempt_number,
            "idempotent": True,
        }
    session.add(
        BatchPredictionAttempt(
            item_key=item_key,
            attempt_number=attempt_number,
            stage=stage,
            outcome=outcome,
            failure_code=failure_code,
            retryable=retryable,
            attempt_checksum=digest,
            created_at=datetime.now(UTC),
        )
    )
    return {
        "attempt_checksum": digest,
        "attempt_number": attempt_number,
        "retryable": retryable,
        "idempotent": False,
    }


def aggregate_batch(session: Session, batch_id: str) -> dict:
    items = session.scalars(
        select(BatchPredictionItem).where(BatchPredictionItem.batch_id == batch_id)
    ).all()
    counts: dict[str, int] = {}
    for item in items:
        key = item.outcome or item.status
        counts[key] = counts.get(key, 0) + 1
    completed = sum(
        value
        for key, value in counts.items()
        if key
        in {"validated", "validated_with_warning", "rejected", "abstain", "governance_completed"}
    )
    status = (
        "completed" if completed == len(items) else "partially_completed" if completed else "failed"
    )
    return {
        "batch_id": batch_id,
        "status": status,
        "item_count": len(items),
        "completed_count": completed,
        "outcomes": counts,
        "checksum": checksum({"batch": batch_id, "counts": counts}),
    }


def execute_callable_item(
    session: Session,
    batch_id: str,
    item_key: str,
    rows: list[dict],
    artifact: bytes,
    artifact_checksum: str,
    version_identity: str,
    load_policy: LoadPolicy,
    prediction_policy: PredictionPolicy,
    store: HandleStore,
    safety_rules: dict[str, dict],
    statistical_outcome: dict,
) -> dict:
    contract = load_callable_handle(
        artifact, artifact_checksum, "json_manifest", version_identity, load_policy
    )
    store.add(contract.handle)
    prediction = persist_prediction(
        session, item_key, version_identity, rows, contract.predict(rows), prediction_policy
    )
    return execute_governed_item(
        session,
        batch_id,
        item_key,
        prediction["prediction_identity"],
        safety_rules,
        statistical_outcome,
    )


def plan_partitions(session: Session, batch_id: str) -> dict:
    request = session.scalar(
        select(BatchPredictionRequest).where(BatchPredictionRequest.batch_id == batch_id)
    )
    if request is None:
        raise ValueError("batch_not_found")
    if session.scalar(
        select(BatchPredictionPartition).where(BatchPredictionPartition.batch_id == batch_id)
    ):
        return {"batch_id": batch_id, "status": "planned"}
    items = session.scalars(
        select(BatchPredictionItem)
        .where(BatchPredictionItem.batch_id == batch_id)
        .order_by(BatchPredictionItem.ordinal)
    ).all()
    partitions = []
    for number, start in enumerate(range(0, len(items), 50)):
        chunk = items[start : start + 50]
        payload = {
            "batch_id": batch_id,
            "number": number,
            "first": chunk[0].ordinal,
            "last": chunk[-1].ordinal,
        }
        session.add(
            BatchPredictionPartition(
                batch_id=batch_id,
                partition_number=number,
                first_ordinal=chunk[0].ordinal,
                last_ordinal=chunk[-1].ordinal,
                status="planned",
                checksum=checksum(payload),
                created_at=datetime.now(UTC),
            )
        )
        partitions.append(payload)
    request.status = "planned"
    session.add(
        BatchPredictionCheckpoint(
            batch_id=batch_id,
            checkpoint_type="partitions_planned",
            sequence=1,
            state_checksum=checksum(partitions),
            created_at=datetime.now(UTC),
        )
    )
    return {"batch_id": batch_id, "status": "planned", "partition_count": len(partitions)}


def cancel_batch(session: Session, batch_id: str, requested_by: str, reason: str) -> dict:
    if not reason.strip():
        raise ValueError("cancellation_reason_required")
    request = session.scalar(
        select(BatchPredictionRequest).where(BatchPredictionRequest.batch_id == batch_id)
    )
    if request is None:
        raise ValueError("batch_not_found")
    existing = session.scalar(
        select(BatchPredictionCancellation).where(BatchPredictionCancellation.batch_id == batch_id)
    )
    if existing:
        return {"batch_id": batch_id, "status": existing.status}
    request.status = "cancelled"
    session.add(
        BatchPredictionCancellation(
            batch_id=batch_id,
            requested_by=requested_by,
            reason=reason,
            status="completed",
            created_at=datetime.now(UTC),
        )
    )
    return {"batch_id": batch_id, "status": "cancelled"}


def execute_governed_item(
    session: Session,
    batch_id: str,
    item_key: str,
    prediction_identity: str,
    safety_rules: dict[str, dict],
    statistical_outcome: dict,
) -> dict:
    """Finalize an already-created offline prediction through every governance layer."""
    item = session.scalar(
        select(BatchPredictionItem).where(
            BatchPredictionItem.item_key == item_key, BatchPredictionItem.batch_id == batch_id
        )
    )
    if item is None:
        raise ValueError("batch_item_not_found")
    validation_request = request_validation(
        session, prediction_identity, "batch-worker", "controlled batch validation"
    )
    validation = execute_validation(session, validation_request["request_identity"])
    safety = persist_safety_result(session, prediction_identity, safety_rules)
    governance = persist_governance(
        session,
        prediction_identity,
        {"structural": validation, "statistical": statistical_outcome, "safety": safety},
    )
    item.status = "governance_completed"
    item.outcome = governance["decision"]
    return {
        "item_key": item_key,
        "prediction_identity": prediction_identity,
        "validation": validation,
        "safety": safety,
        "governance": governance,
    }


def acquire_lease(
    session: Session, batch_id: str, partition_id: str, worker_key: str, ttl_seconds: int = 300
) -> dict:
    now = datetime.now(UTC)
    active = session.scalar(
        select(BatchPredictionWorkerLease).where(
            BatchPredictionWorkerLease.partition_id == partition_id,
            BatchPredictionWorkerLease.status == "active",
        )
    )
    if active and active.expires_at > now:
        raise ValueError("partition_lease_active")
    if active:
        active.status = "expired"
    token_hash = checksum(
        {"batch": batch_id, "partition": partition_id, "worker": worker_key, "at": now.isoformat()}
    )
    session.add(
        BatchPredictionWorkerLease(
            batch_id=batch_id,
            partition_id=partition_id,
            worker_key=worker_key,
            lease_token_hash=token_hash,
            status="active",
            expires_at=now.replace(microsecond=0) + timedelta(seconds=ttl_seconds),
            created_at=now,
        )
    )
    return {
        "partition_id": partition_id,
        "worker_key": worker_key,
        "lease_token_hash": token_hash,
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
    }


def replay_batch(session: Session, source_batch_id: str, mode: str = "exact") -> dict:
    if mode not in {"exact", "failed_items_only"}:
        raise ValueError("unsupported_replay_mode")
    source = session.scalar(
        select(BatchPredictionRequest).where(BatchPredictionRequest.batch_id == source_batch_id)
    )
    if source is None:
        raise ValueError("batch_not_found")
    replay_id = checksum({"source": source_batch_id, "mode": mode})
    existing = session.scalar(
        select(BatchPredictionReplay).where(BatchPredictionReplay.replay_batch_id == replay_id)
    )
    if existing:
        return {"replay_batch_id": replay_id, "idempotent": True}
    session.add(
        BatchPredictionReplay(
            source_batch_id=source_batch_id,
            replay_batch_id=replay_id,
            mode=mode,
            checksum=checksum({"source": source_batch_id, "mode": mode}),
            created_at=datetime.now(UTC),
        )
    )
    return {
        "replay_batch_id": replay_id,
        "source_batch_id": source_batch_id,
        "mode": mode,
        "idempotent": False,
    }
