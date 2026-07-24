from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

RULES = (
    "prediction_exists",
    "manifest_exists",
    "output_validated",
    "prediction_checksum_valid",
    "manifest_checksum_valid",
    "model_approved",
    "policy_enabled",
    "prediction_immutable",
    "prediction_not_invalidated",
    "prediction_not_superseded",
)


@dataclass(frozen=True)
class Eligibility:
    status: str
    reason: str | None = None


def checksum(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def assess_eligibility(
    prediction: dict | None, policy: dict | None, manifest: dict | None
) -> Eligibility:
    if prediction is None:
        return Eligibility("ineligible", "missing_prediction")
    if prediction.get("status") != "completed":
        return Eligibility("invalid_prediction", "prediction_not_completed")
    if manifest is None:
        return Eligibility("ineligible", "missing_manifest")
    if prediction.get("invalidated"):
        return Eligibility("prediction_invalidated")
    if prediction.get("superseded"):
        return Eligibility("prediction_superseded")
    if not policy or not policy.get("enabled", False):
        return Eligibility("policy_disabled")
    return Eligibility("eligible")


def execute_rules(
    prediction: dict | None, policy: dict | None, manifest: dict | None
) -> list[dict]:
    assess_eligibility(prediction, policy, manifest)
    checks = {
        "prediction_exists": prediction is not None,
        "manifest_exists": manifest is not None,
        "output_validated": bool(prediction and prediction.get("output_validated", True)),
        "prediction_checksum_valid": bool(prediction and prediction.get("checksum_valid", True)),
        "manifest_checksum_valid": bool(manifest and manifest.get("checksum_valid", True)),
        "model_approved": bool(
            prediction and prediction.get("model_status", "approved") == "approved"
        ),
        "policy_enabled": bool(policy and policy.get("enabled", False)),
        "prediction_immutable": not bool(prediction and prediction.get("mutable", False)),
        "prediction_not_invalidated": not bool(prediction and prediction.get("invalidated", False)),
        "prediction_not_superseded": not bool(prediction and prediction.get("superseded", False)),
    }
    return [{"rule_code": rule, "passed": checks[rule]} for rule in RULES]
