from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import OfflinePredictionRecord
from app.offline_prediction.core import (
    PredictionPolicy,
    normalize_output,
    prediction_identity,
    validate_request,
)


def persist_prediction(
    session: Session,
    request_id: str,
    model_version: str,
    rows: list[dict],
    outputs: list[object],
    policy: PredictionPolicy,
) -> dict:
    validate_request(rows, policy)
    normalized = [normalize_output(value) for value in outputs]
    identity = prediction_identity(request_id, model_version, normalized)
    payload = {
        "request_id": request_id,
        "model_version": model_version,
        "outputs": normalized,
        "offline_only": True,
        "prediction_identity": identity,
    }
    if (
        session.scalar(
            select(OfflinePredictionRecord).where(
                OfflinePredictionRecord.prediction_identity == identity
            )
        )
        is None
    ):
        session.add(
            OfflinePredictionRecord(
                prediction_identity=identity,
                request_id=request_id,
                model_version=model_version,
                status="completed",
                payload=payload,
                lineage={"row_count": len(rows), "policy": policy.code},
                offline_only=True,
                created_at=datetime.now(UTC),
            )
        )
    return payload
