from datetime import UTC, datetime
from hashlib import sha256
import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import ModelCandidateRecord
from app.candidate_registry.core import RegistrationPolicy, evaluate_registration


def register_candidate(
    session: Session,
    version_identity: str,
    preconditions: dict,
    policy: RegistrationPolicy,
    payload: dict,
) -> dict:
    decision = evaluate_registration(preconditions, policy)
    if not decision["registrable"]:
        return {"registered": False, "decision": decision}
    candidate_identity = sha256(
        json.dumps(
            {
                "version_identity": version_identity,
                "registration_identity": decision["registration_identity"],
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    if (
        session.scalar(
            select(ModelCandidateRecord).where(
                ModelCandidateRecord.candidate_identity == candidate_identity
            )
        )
        is None
    ):
        session.add(
            ModelCandidateRecord(
                candidate_identity=candidate_identity,
                version_identity=version_identity,
                registration_identity=decision["registration_identity"],
                status="registered",
                payload=payload,
                lineage={"preconditions": preconditions, "policy": policy.code},
                created_at=datetime.now(UTC),
            )
        )
    return {"registered": True, "candidate_identity": candidate_identity, "status": "registered"}
