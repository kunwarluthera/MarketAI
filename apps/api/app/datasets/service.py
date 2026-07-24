from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.models import MLDataset
from app.datasets.builder import DatasetSpec, build_dataset


def persist_dataset(session: Session, snapshots: list[dict], spec: DatasetSpec) -> dict:
    payload = build_dataset(snapshots, spec)
    row = session.scalar(
        select(MLDataset).where(MLDataset.dataset_identity == payload["dataset_identity"])
    )
    if row is None:
        manifest = {
            "dataset_identity": payload["dataset_identity"],
            "dataset_code": spec.dataset_code,
            "dataset_version": spec.dataset_version,
            "row_count": payload["row_count"],
            "contains_labels": False,
            "source_snapshot_ids": [x.get("snapshot_identity") for x in snapshots],
        }
        session.add(
            MLDataset(
                dataset_identity=payload["dataset_identity"],
                dataset_code=spec.dataset_code,
                dataset_version=spec.dataset_version,
                schema_version=payload["dataset_schema_version"],
                row_count=payload["row_count"],
                manifest=manifest,
                payload=payload,
                created_at=datetime.now(UTC),
            )
        )
    return payload
