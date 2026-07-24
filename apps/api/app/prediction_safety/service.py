from __future__ import annotations

from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.models import (
    PredictionSafetyEvent,
    PredictionSafetyManifest,
    PredictionSafetyPolicy,
    PredictionSafetyResult,
    PredictionSafetyEvidence,
)
from app.prediction_safety.core import checksum, run_safety_gates


def persist_safety_result(
    session: Session, prediction_identity: str, rules: dict[str, dict]
) -> dict:
    policy = session.scalar(
        select(PredictionSafetyPolicy).where(
            PredictionSafetyPolicy.policy_code == "CONTROLLED_PREDICTION_SAFETY_V1"
        )
    )
    enabled = bool(policy and policy.enabled)
    eligibility = rules.get("eligibility", {"status": "failed", "reason": "missing_eligibility"})
    integrity = rules.get("integrity", {"status": "incomplete", "reason": "missing_integrity"})
    ood = rules.get("ood", {"status": "incomplete", "reason": "missing_ood"})
    regime = rules.get("regime", {"status": "incomplete", "reason": "missing_regime"})
    if not enabled:
        eligibility = {"status": "failed", "reason": "policy_disabled"}
    decision = run_safety_gates(
        eligibility=eligibility, integrity=integrity, ood=ood, regime=regime
    )
    identity = checksum({"prediction": prediction_identity, "decision": decision})
    existing = session.scalar(
        select(PredictionSafetyResult).where(PredictionSafetyResult.safety_identity == identity)
    )
    if existing:
        return {
            "safety_identity": identity,
            "decision": existing.decision,
            "result_checksum": existing.result_checksum,
        }
    session.add(
        PredictionSafetyResult(
            safety_identity=identity,
            prediction_identity=prediction_identity,
            decision=decision["decision"],
            rule_results=[eligibility, integrity, ood, regime],
            result_checksum=checksum(decision),
            created_at=datetime.now(UTC),
        )
    )
    for evidence_type, payload in (("integrity", integrity), ("ood", ood), ("regime", regime)):
        evidence_payload = {
            "safety_identity": identity,
            "evidence_type": evidence_type,
            "payload": payload,
        }
        evidence_checksum = checksum(evidence_payload)
        session.add(
            PredictionSafetyEvidence(
                evidence_identity=evidence_checksum,
                safety_identity=identity,
                evidence_type=evidence_type,
                payload=payload,
                evidence_checksum=evidence_checksum,
                created_at=datetime.now(UTC),
            )
        )
    manifest_payload = {"prediction_identity": prediction_identity, "decision": decision}
    manifest_checksum = checksum(manifest_payload)
    session.add(
        PredictionSafetyManifest(
            manifest_identity=manifest_checksum,
            safety_identity=identity,
            payload=manifest_payload,
            manifest_checksum=manifest_checksum,
            created_at=datetime.now(UTC),
        )
    )
    session.add(
        PredictionSafetyEvent(
            event_identity=checksum({"safety": identity, "event": "safety_completed"}),
            safety_identity=identity,
            event_type="safety_completed",
            payload={"decision": decision["decision"]},
            created_at=datetime.now(UTC),
        )
    )
    return {
        "safety_identity": identity,
        "decision": decision["decision"],
        "manifest_checksum": manifest_checksum,
    }
