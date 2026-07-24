from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.models import OpportunityRecord
from app.opportunity.engine import OpportunityInput, OpportunityResult, evaluate_opportunity


RULE_VERSION = "2.5.1"


def evaluate_and_store(session: Session, inputs: OpportunityInput) -> OpportunityResult:
    result = evaluate_opportunity(inputs)
    existing = session.scalar(
        select(OpportunityRecord).where(
            OpportunityRecord.instrument_id == result.instrument_id,
            OpportunityRecord.evaluated_at == result.evaluated_at,
            OpportunityRecord.rule_version == RULE_VERSION,
        )
    )
    payload = dict(
        expires_at=result.expires_at,
        orientation=result.orientation,
        state=result.state,
        score=result.score,
        blockers=list(result.blocking_reasons),
        cautions=list(result.caution_flags),
        contributions=list(result.contributions),
        lineage={"rule_version": RULE_VERSION, "evaluated_at": result.evaluated_at.isoformat()},
    )
    if existing is None:
        existing = OpportunityRecord(
            instrument_id=result.instrument_id,
            evaluated_at=result.evaluated_at,
            rule_version=RULE_VERSION,
            created_at=datetime.utcnow(),
            **payload,
        )
        session.add(existing)
    else:
        for key, value in payload.items():
            setattr(existing, key, value)
    return result
