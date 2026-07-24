from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.models import MLLabelRecord
from app.labels.framework import LabelSpec, OutcomeSpec, calculate_raw_outcome, derive_label


def persist_label(
    session: Session, row: dict, future_bars: list[dict], outcome: OutcomeSpec, label: LabelSpec
) -> dict:
    raw = calculate_raw_outcome(row, future_bars, outcome)
    result = derive_label(raw, label)
    identity = result.get(
        "label_identity", f"{row.get('snapshot_identity')}:{label.label_code}:{label.label_version}"
    )
    existing = session.scalar(select(MLLabelRecord).where(MLLabelRecord.row_identity == identity))
    if existing is None:
        session.add(
            MLLabelRecord(
                row_identity=identity,
                outcome_code=outcome.outcome_code,
                outcome_version=outcome.outcome_version,
                label_code=label.label_code,
                label_version=label.label_version,
                status=result["status"],
                feature_cutoff_at=row["evaluated_at"],
                available_at=result.get("available_at"),
                payload={"raw": raw, "label": result},
                lineage={
                    "source_snapshot": row.get("snapshot_identity"),
                    "future_bar_count": len(future_bars),
                },
                created_at=datetime.now(UTC),
            )
        )
    return result
