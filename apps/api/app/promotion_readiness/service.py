from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.promotion_readiness.core import evaluate
from app.common.models import PromotionReadinessPolicy, PromotionReadiness


def run_readiness(session: Session, model_id: str, dataset_id: str, evidence: dict) -> dict:
    policy = session.scalar(
        select(PromotionReadinessPolicy).where(
            PromotionReadinessPolicy.policy_code == "CONTROLLED_PROMOTION_READINESS_V1"
        )
    )
    if policy is None or not policy.enabled:
        raise ValueError("policy_disabled")
    result = evaluate(evidence, (policy.payload or {}).get("required", []))
    identity = result["checksum"]
    if session.scalar(
        select(PromotionReadiness).where(PromotionReadiness.readiness_id == identity)
    ):
        return {"readiness_id": identity, **result, "idempotent": True}
    session.add(
        PromotionReadiness(
            readiness_id=identity,
            model_id=model_id,
            dataset_id=dataset_id,
            payload=result,
            checksum=identity,
            created_at=datetime.now(UTC),
        )
    )
    return {"readiness_id": identity, **result, "idempotent": False}
