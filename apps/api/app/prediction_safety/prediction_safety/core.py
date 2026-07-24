from __future__ import annotations

from hashlib import sha256
import json
import math


def checksum(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def safety_eligibility(
    *,
    statistical_decision: str | None,
    prediction_immutable: bool,
    prediction_manifest: bool,
    statistical_manifest: bool,
    model_approved: bool,
    policy_enabled: bool,
    invalidated: bool = False,
    superseded: bool = False,
) -> dict:
    if not policy_enabled:
        return {"status": "ineligible", "reason": "policy_disabled"}
    if statistical_decision != "validated":
        return {"status": "ineligible", "reason": "missing_statistical_validation"}
    if invalidated:
        return {"status": "ineligible", "reason": "prediction_invalidated"}
    if superseded:
        return {"status": "ineligible", "reason": "prediction_superseded"}
    if not prediction_manifest or not statistical_manifest:
        return {"status": "ineligible", "reason": "missing_manifest"}
    if not prediction_immutable or not model_approved:
        return {"status": "ineligible", "reason": "prediction_integrity_failed"}
    return {"status": "eligible", "reason": None}


def validate_input_integrity(
    features: list[object],
    required_features: list[str],
    feature_names: list[str],
    declared_checksum: str | None,
    schema_version: str | None,
    expected_schema_version: str,
) -> dict:
    if schema_version != expected_schema_version:
        return {"status": "failed", "reason": "schema_version_invalid"}
    if feature_names != required_features or len(features) != len(required_features):
        return {"status": "failed", "reason": "feature_schema_invalid"}
    if any(
        value is None or (isinstance(value, float) and not math.isfinite(value))
        for value in features
    ):
        return {"status": "failed", "reason": "feature_value_invalid"}
    actual = checksum(
        {"schema_version": schema_version, "feature_names": feature_names, "features": features}
    )
    if declared_checksum != actual:
        return {"status": "failed", "reason": "feature_checksum_invalid"}
    return {"status": "passed", "reason": "input_integrity_valid", "checksum": actual}
