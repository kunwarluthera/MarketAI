from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.models import ResearchSnapshot
from app.research.snapshot import ResearchSnapshotInput, build_snapshot


def persist_snapshot(session: Session, inputs: ResearchSnapshotInput) -> dict:
    payload = build_snapshot(inputs)
    row = session.scalar(
        select(ResearchSnapshot).where(
            ResearchSnapshot.snapshot_identity == payload["snapshot_identity"]
        )
    )
    if row is None:
        session.add(
            ResearchSnapshot(
                snapshot_identity=payload["snapshot_identity"],
                instrument_id=inputs.instrument_id,
                evaluated_at=inputs.evaluated_at,
                schema_version=payload["schema_version"],
                payload=payload,
                lineage=inputs.lineage,
                created_at=datetime.now(UTC),
            )
        )
    return payload
