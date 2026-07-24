from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import MetricAggregationReport
from app.metric_aggregation.core import build_report


def persist_report(
    session: Session,
    validation_id: str,
    folds: list[dict],
    metrics: tuple[str, ...] = ("accuracy",),
) -> dict:
    payload = build_report(validation_id, folds, metrics)
    if (
        session.scalar(
            select(MetricAggregationReport).where(
                MetricAggregationReport.report_identity == payload["report_identity"]
            )
        )
        is None
    ):
        session.add(
            MetricAggregationReport(
                report_identity=payload["report_identity"],
                validation_id=validation_id,
                fold_count=len(folds),
                payload=payload,
                lineage={"fold_count": len(folds)},
                research_only=True,
                created_at=datetime.now(UTC),
            )
        )
    return payload
