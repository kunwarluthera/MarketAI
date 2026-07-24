from __future__ import annotations

from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.models import (
    PredictionGovernanceDecision,
    PredictionGovernanceEvent,
    PredictionGovernanceManifest,
    PredictionGovernancePolicy,
)
from app.prediction_governance.core import aggregate_outcomes, checksum


def persist_governance(
    session: Session, prediction_identity: str, outcomes: dict[str, dict]
) -> dict:
    policy = session.scalar(
        select(PredictionGovernancePolicy).where(
            PredictionGovernancePolicy.policy_code == "CONTROLLED_VALIDATION_GOVERNANCE_V1"
        )
    )
    decision = aggregate_outcomes(
        outcomes.get("structural", {}),
        outcomes.get("statistical", {}),
        outcomes.get("safety", {}),
        policy_enabled=bool(policy and policy.enabled),
        immutable=bool(outcomes.get("immutable", True)),
        manifests_exist=bool(outcomes.get("manifests_exist", True)),
    )
    identity = checksum({"prediction": prediction_identity, "decision": decision})
    existing = session.scalar(
        select(PredictionGovernanceDecision).where(
            PredictionGovernanceDecision.governance_identity == identity
        )
    )
    if existing:
        return {
            "governance_identity": identity,
            "decision": existing.decision,
            "decision_checksum": existing.decision_checksum,
        }
    session.add(
        PredictionGovernanceDecision(
            governance_identity=identity,
            prediction_identity=prediction_identity,
            decision=decision["decision"],
            payload={"prediction_identity": prediction_identity, "decision": decision},
            decision_checksum=decision["checksum"],
            created_at=datetime.now(UTC),
        )
    )
    manifest_payload = {
        "governance_identity": identity,
        "prediction_identity": prediction_identity,
        "decision": decision,
    }
    manifest_checksum = checksum(manifest_payload)
    session.add(
        PredictionGovernanceManifest(
            manifest_identity=manifest_checksum,
            governance_identity=identity,
            payload=manifest_payload,
            manifest_checksum=manifest_checksum,
            created_at=datetime.now(UTC),
        )
    )
    session.add(
        PredictionGovernanceEvent(
            event_identity=checksum({"governance": identity, "event": "governance_completed"}),
            governance_identity=identity,
            event_type="governance_completed",
            payload={"decision": decision["decision"]},
            created_at=datetime.now(UTC),
        )
    )
    return {
        "governance_identity": identity,
        "decision": decision["decision"],
        "manifest_checksum": manifest_checksum,
    }
