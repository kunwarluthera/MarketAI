from __future__ import annotations

from hashlib import sha256
import json


def checksum(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def aggregate_outcomes(structural: dict, statistical: dict, safety: dict, *, policy_enabled: bool, immutable: bool, manifests_exist: bool) -> dict:
    if not policy_enabled:
        decision = "rejected"
        reason = "policy_disabled"
    elif not immutable or not manifests_exist:
        decision = "rejected"
        reason = "governance_eligibility_failed"
    elif structural.get("decision") != "validated":
        decision = "rejected"
        reason = "structural_validation_failed"
    elif statistical.get("decision") not in {"validated", "validated_with_warnings"}:
        decision = "abstain"
        reason = "statistical_validation_failed"
    elif safety.get("decision") not in {"safe", "validated"}:
        decision = "abstain"
        reason = "safety_validation_failed"
    elif "warning" in {structural.get("severity"), statistical.get("severity"), safety.get("severity")}:
        decision = "validated_with_warning"
        reason = "validation_warning"
    else:
        decision = "validated"
        reason = None
    return {"decision": decision, "reason": reason, "checksum": checksum({"structural": structural, "statistical": statistical, "safety": safety, "policy_enabled": policy_enabled, "immutable": immutable, "manifests_exist": manifests_exist})}
