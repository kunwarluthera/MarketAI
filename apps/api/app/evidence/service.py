from __future__ import annotations
from datetime import UTC, datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import EvidenceEvaluation, uid
from .engine import REGISTRY, evaluate


def persist_evidence(
    session: Session,
    instrument_id: str,
    interval: str,
    code: str,
    evaluation_time: datetime,
    inputs: dict,
    lineage: dict | None = None,
) -> EvidenceEvaluation:
    definition = REGISTRY[code]
    result = evaluate(code, inputs, evaluation_time)
    row = session.scalar(
        select(EvidenceEvaluation).where(
            EvidenceEvaluation.instrument_id == instrument_id,
            EvidenceEvaluation.interval == interval,
            EvidenceEvaluation.evaluation_time == evaluation_time,
            EvidenceEvaluation.evidence_code == code,
            EvidenceEvaluation.rule_version == definition.rule_version,
        )
    )
    if row is None:
        row = EvidenceEvaluation(
            id=uid(),
            instrument_id=instrument_id,
            interval=interval,
            evaluation_time=evaluation_time,
            evidence_code=code,
            rule_version=definition.rule_version,
            category=definition.category,
            direction=result["direction"],
            state=result["state"],
            strength=Decimal(str(result["strength"])),
            expires_at=result["expires_at"],
            readiness="ready" if result["direction"] != "unavailable" else "not_ready",
            inputs=inputs,
            lineage=lineage or {},
            created_at=datetime.now(UTC),
        )
        session.add(row)
    else:
        row.direction, row.state, row.strength, row.expires_at = (
            result["direction"],
            result["state"],
            Decimal(str(result["strength"])),
            result["expires_at"],
        )
    session.flush()
    return row


def readiness(inputs: dict) -> dict:
    blockers = [
        key
        for key in ("provider_fresh", "instrument_active", "features_complete")
        if inputs.get(key) is False
    ]
    missing = inputs.get("missing_features", [])
    return {
        "status": "not_ready" if blockers or missing else "ready",
        "blocking_reasons": blockers,
        "missing_features": missing,
    }
