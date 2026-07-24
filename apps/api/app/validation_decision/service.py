from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import ValidationDecisionRecord
from app.validation_decision.core import ValidationPolicy, evaluate_policy


def persist_decision(
    session: Session, validation_id: str, metrics: dict, policy: ValidationPolicy
) -> dict:
    payload = evaluate_policy(metrics, policy)
    if (
        session.scalar(
            select(ValidationDecisionRecord).where(
                ValidationDecisionRecord.decision_identity == payload["decision_identity"]
            )
        )
        is None
    ):
        session.add(
            ValidationDecisionRecord(
                decision_identity=payload["decision_identity"],
                validation_id=validation_id,
                policy_code=policy.code,
                policy_version=policy.version,
                decision=payload["decision"],
                payload=payload,
                lineage={"validation_id": validation_id},
                research_only=True,
                created_at=datetime.now(UTC),
            )
        )
    return payload
