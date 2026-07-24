from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.global_explainability.core import aggregate
from app.attribution.core import checksum
from app.common.models import (
    GlobalExplanation,
    GlobalImportance,
    GlobalStability,
    GlobalExplainabilityPolicy,
)


def create_global(
    session: Session,
    dataset_identity: str,
    model_identity: str,
    rows: list[dict],
    sample_count: int,
) -> dict:
    policy = session.scalar(
        select(GlobalExplainabilityPolicy).where(
            GlobalExplainabilityPolicy.policy_code == "CONTROLLED_GLOBAL_EXPLAINABILITY_V1"
        )
    )
    if policy is None or not policy.enabled:
        raise ValueError("policy_disabled")
    if sample_count < policy.minimum_sample_size:
        raise ValueError("minimum_sample_size")
    if rows and any(row.get("mutable") or row.get("is_live") for row in rows):
        raise ValueError("mutable_dataset_rejected")
    result = aggregate(rows, policy.aggregation_strategy, policy.top_feature_limit)
    identity = checksum(
        {
            "dataset": dataset_identity,
            "model": model_identity,
            "policy": policy.policy_code,
            "result": result,
        }
    )
    if session.scalar(
        select(GlobalExplanation).where(GlobalExplanation.explanation_identity == identity)
    ):
        return {"explanation_identity": identity, "idempotent": True}
    session.add(
        GlobalExplanation(
            explanation_identity=identity,
            dataset_identity=dataset_identity,
            model_identity=model_identity,
            payload=result,
            checksum=identity,
            created_at=datetime.now(UTC),
        )
    )
    for row in result["features"]:
        session.add(
            GlobalImportance(
                explanation_identity=identity,
                feature_name=row["feature_name"],
                payload=row,
                created_at=datetime.now(UTC),
            )
        )
    session.add(
        GlobalStability(
            explanation_identity=identity, payload=result["stability"], created_at=datetime.now(UTC)
        )
    )
    return {"explanation_identity": identity, "checksum": identity, "idempotent": False}
