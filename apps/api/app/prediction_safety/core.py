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


def validate_ood_bounds(values: dict[str, float], bounds: dict[str, dict[str, float]]) -> dict:
    violations = []
    for name, value in values.items():
        limit = bounds.get(name)
        if (
            limit is None
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < limit["lower"]
            or value > limit["upper"]
        ):
            violations.append(name)
    return {
        "status": "passed" if not violations else "failed",
        "reason": "ood_bounds_passed" if not violations else "ood_bounds_failed",
        "violations": violations,
    }


def validate_regime_compatibility(regime: str | None, allowed_regimes: list[str]) -> dict:
    if regime is None:
        return {"status": "incomplete", "reason": "regime_missing"}
    return {
        "status": "passed" if regime in allowed_regimes else "failed",
        "reason": "regime_compatible" if regime in allowed_regimes else "regime_incompatible",
    }


def aggregate_safety_decision(results: list[dict], *, abstention_enabled: bool = True) -> dict:
    failures = [item.get("reason") for item in results if item.get("status") == "failed"]
    incomplete = [item.get("reason") for item in results if item.get("status") == "incomplete"]
    passed = not failures and not incomplete
    return {
        "decision": "safe" if passed else "unsafe",
        "abstain": abstention_enabled and not passed,
        "blocking_reasons": failures,
        "incomplete_reasons": incomplete,
        "rule_count": len(results),
        "checksum": checksum({"results": results, "abstention_enabled": abstention_enabled}),
    }


def run_safety_gates(
    *, eligibility: dict, integrity: dict, ood: dict, regime: dict, abstention_enabled: bool = True
) -> dict:
    return aggregate_safety_decision(
        [eligibility, integrity, ood, regime], abstention_enabled=abstention_enabled
    )
