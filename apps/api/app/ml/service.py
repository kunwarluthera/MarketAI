from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.models import MLTrainingRun


def persist_training_run(session: Session, manifest: dict, metrics: dict) -> dict:
    identity = manifest["training_identity"]
    row = session.scalar(select(MLTrainingRun).where(MLTrainingRun.training_identity == identity))
    if row is None:
        session.add(
            MLTrainingRun(
                training_identity=identity,
                dataset_identity=manifest["dataset_identity"],
                label_spec=manifest["label_spec"],
                algorithm=manifest["algorithm"],
                status="completed",
                metrics=metrics,
                lineage={"split_counts": manifest["split_counts"]},
                research_only=True,
                created_at=datetime.now(UTC),
            )
        )
    return {"training_identity": identity, "metrics": metrics, "research_only": True}
