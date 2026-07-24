from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.regime_evaluation.core import evaluate
from app.common.models import RegimeEvaluationPolicy, RegimeEvaluation


def run_evaluation(session: Session, evaluation_id: str, groups: dict[str, list[float]]) -> dict:
    policy = session.scalar(
        select(RegimeEvaluationPolicy).where(
            RegimeEvaluationPolicy.policy_code == "CONTROLLED_REGIME_EVALUATION_V1"
        )
    )
    if policy is None or not policy.enabled:
        raise ValueError("policy_disabled")
    result = evaluate(groups, policy.minimum_samples)
    identity = result["checksum"]
    if session.scalar(
        select(RegimeEvaluation).where(RegimeEvaluation.evaluation_identity == identity)
    ):
        return {"evaluation_identity": identity, **result, "idempotent": True}
    session.add(
        RegimeEvaluation(
            evaluation_identity=identity,
            source_evaluation_id=evaluation_id,
            payload=result,
            checksum=identity,
            created_at=datetime.now(UTC),
        )
    )
    return {"evaluation_identity": identity, **result, "idempotent": False}
