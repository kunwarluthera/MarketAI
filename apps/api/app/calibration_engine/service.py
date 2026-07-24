from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.calibration_engine.core import calibrate
from app.common.models import CalibrationPolicy, CalibrationReliability


def run_calibration(
    session: Session, evaluation_id: str, probabilities: list[float], outcomes: list[int]
) -> dict:
    policy = session.scalar(
        select(CalibrationPolicy).where(
            CalibrationPolicy.policy_code == "CONTROLLED_CALIBRATION_V1"
        )
    )
    if policy is None or not policy.enabled:
        raise ValueError("policy_disabled")
    if len(probabilities) < policy.minimum_samples:
        raise ValueError("minimum_samples")
    result = calibrate(probabilities, outcomes, policy.maximum_bins)
    if session.scalar(
        select(CalibrationReliability).where(
            CalibrationReliability.reliability_checksum == result["checksum"]
        )
    ):
        return {**result, "idempotent": True}
    session.add(
        CalibrationReliability(
            evaluation_id=evaluation_id,
            payload=result,
            reliability_checksum=result["checksum"],
            created_at=datetime.now(UTC),
        )
    )
    return {**result, "idempotent": False}
