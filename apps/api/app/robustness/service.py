from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import RobustnessReport
from app.robustness.core import robustness_summary


def persist_robustness(
    session: Session, validation_id: str, folds: list[dict], metric: str = "accuracy"
) -> dict:
    payload = robustness_summary(folds, metric=metric)
    if (
        session.scalar(
            select(RobustnessReport).where(
                RobustnessReport.summary_identity == payload["summary_identity"]
            )
        )
        is None
    ):
        session.add(
            RobustnessReport(
                summary_identity=payload["summary_identity"],
                validation_id=validation_id,
                payload=payload,
                lineage={"fold_count": len(folds), "metric": metric},
                historical_only=True,
                created_at=datetime.now(UTC),
            )
        )
    return payload
