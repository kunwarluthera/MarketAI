from datetime import UTC, datetime
from hashlib import sha256
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import PromotionRequestRecord
from app.promotion.core import PromotionPolicy, evaluate_eligibility


def create_request(
    session: Session,
    candidate_identity: str,
    candidate: dict,
    policy: PromotionPolicy,
    stage: str = "review",
) -> dict:
    decision = evaluate_eligibility(candidate, policy)
    payload = {
        "candidate_identity": candidate_identity,
        "stage": stage,
        "eligibility": decision,
        "decision": "needs_review"
        if decision["decision"] == "promotion_eligible"
        else "rejected_for_promotion",
    }
    identity = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    if (
        session.scalar(
            select(PromotionRequestRecord).where(
                PromotionRequestRecord.request_identity == identity
            )
        )
        is None
    ):
        session.add(
            PromotionRequestRecord(
                request_identity=identity,
                candidate_identity=candidate_identity,
                stage=stage,
                decision=payload["decision"],
                payload=payload,
                lineage={"policy": policy.code},
                created_at=datetime.now(UTC),
            )
        )
    return {"request_identity": identity, **payload}
