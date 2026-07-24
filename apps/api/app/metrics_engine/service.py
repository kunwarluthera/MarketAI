from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.metrics_engine.core import compute
from app.common.models import MetricPolicy, MetricResult


def calculate(
    session: Session, evaluation_id: str, metric: str, actual: list[float], predicted: list[float]
) -> dict:
    policy = session.scalar(
        select(MetricPolicy).where(MetricPolicy.policy_code == "CONTROLLED_METRICS_V1")
    )
    if (
        policy is None
        or not policy.enabled
        or metric not in (policy.payload or {}).get("metrics", [])
    ):
        raise ValueError("metric_not_allowed")
    result = compute(metric, actual, predicted)
    identity = result["checksum"]
    if session.scalar(select(MetricResult).where(MetricResult.result_checksum == identity)):
        return {**result, "idempotent": True}
    session.add(
        MetricResult(
            evaluation_id=evaluation_id,
            metric=metric,
            family=result["family"],
            payload=result,
            result_checksum=identity,
            created_at=datetime.now(UTC),
        )
    )
    return {**result, "idempotent": False}
