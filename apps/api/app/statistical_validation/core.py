from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from datetime import datetime


@dataclass(frozen=True)
class StatisticalPolicy:
    code: str = "CONTROLLED_STATISTICAL_PREDICTION_VALIDATION_V1"
    version: str = "1"
    minimum_confidence: float = 0.5
    maximum_entropy: float = 1.0
    probability_tolerance: float = 1e-9


def digest(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def validate_probabilities(
    classes: list[str], probabilities: list[float], tolerance: float = 1e-9
) -> dict:
    if not classes or len(classes) != len(probabilities) or len(set(classes)) != len(classes):
        return {"status": "failed", "reason": "probability_structure_invalid"}
    if any(
        not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or value < 0
        or value > 1
        for value in probabilities
    ):
        return {"status": "failed", "reason": "probability_bounds_invalid"}
    total = math.fsum(probabilities)
    if abs(total - 1.0) > tolerance:
        return {"status": "failed", "reason": "probability_sum_invalid", "sum": total}
    return {"status": "passed", "reason": "probability_valid", "sum": total}


def classification_statistics(
    classes: list[str], probabilities: list[float], policy: StatisticalPolicy
) -> dict:
    check = validate_probabilities(classes, probabilities, policy.probability_tolerance)
    if check["status"] != "passed":
        return {**check, "decision": "validation_failed"}
    ordered = sorted(enumerate(probabilities), key=lambda item: (-item[1], item[0]))
    first_index, first = ordered[0]
    second = ordered[1][1] if len(ordered) > 1 else 0.0
    entropy = -math.fsum(p * math.log(p) for p in probabilities if p > 0)
    max_entropy = math.log(len(probabilities)) if len(probabilities) > 1 else 0.0
    normalized = entropy / max_entropy if max_entropy else 0.0
    margin = first - second
    passed = first >= policy.minimum_confidence and entropy <= policy.maximum_entropy
    return {
        "status": "passed" if passed else "failed",
        "decision": "validated" if passed else "validation_failed",
        "predicted_class": classes[first_index],
        "maximum_probability": first,
        "second_probability": second,
        "margin": margin,
        "entropy": entropy,
        "normalized_entropy": normalized,
        "tie_detected": abs(margin) <= policy.probability_tolerance,
    }


def statistical_decision(statistics: dict, *, abstention_enabled: bool = True) -> dict:
    if statistics.get("decision") == "validated":
        return {"decision": "validated", "abstain": False, "reason": None}
    return {
        "decision": "validation_failed",
        "abstain": abstention_enabled,
        "reason": "statistical_threshold_failed",
    }


def validate_calibration_evidence(evidence: dict, policy: dict) -> dict:
    required = (
        "model_version",
        "output_contract",
        "sample_count",
        "expected_calibration_error",
        "evidence_checksum",
    )
    if any(key not in evidence for key in required):
        return {"status": "incomplete", "reason": "calibration_evidence_missing"}
    if evidence.get("status") not in {"valid", "valid_with_warnings"}:
        return {"status": "failed", "reason": "calibration_evidence_invalid"}
    if evidence["sample_count"] < policy.get("minimum_sample_support", 1):
        return {"status": "failed", "reason": "calibration_support_insufficient"}
    if evidence["expected_calibration_error"] > policy.get("maximum_calibration_error", 1.0):
        return {"status": "failed", "reason": "expected_calibration_error_exceeded"}
    return {"status": "passed", "reason": "calibration_passed"}


def validate_regression(value: float, evidence: dict, policy: dict) -> dict:
    if not math.isfinite(value):
        return {"status": "failed", "reason": "regression_value_invalid"}
    if "lower_bound" in policy and value < policy["lower_bound"]:
        return {"status": "failed", "reason": "regression_lower_bound_failed"}
    if "upper_bound" in policy and value > policy["upper_bound"]:
        return {"status": "failed", "reason": "regression_upper_bound_failed"}
    residual = evidence.get("residual")
    if residual is not None and (
        not isinstance(residual, (int, float)) or not math.isfinite(residual)
    ):
        return {"status": "failed", "reason": "regression_residual_invalid"}
    return {"status": "passed", "reason": "regression_valid"}


def validate_prediction_interval(value: float, interval: dict) -> dict:
    lower, upper = interval.get("lower"), interval.get("upper")
    valid = (
        all(isinstance(item, (int, float)) and math.isfinite(item) for item in (lower, upper))
        and lower <= upper
    )
    return {
        "status": "passed" if valid and lower <= value <= upper else "failed",
        "reason": "interval_passed" if valid and lower <= value <= upper else "interval_failed",
    }


def validate_reference_distribution(value: float, reference: dict, tolerance: float = 0.0) -> dict:
    lower, upper = reference.get("lower"), reference.get("upper")
    valid = (
        all(
            isinstance(item, (int, float)) and math.isfinite(item) for item in (lower, upper, value)
        )
        and lower <= upper
    )
    compatible = valid and lower - tolerance <= value <= upper + tolerance
    return {
        "status": "passed" if compatible else "warning",
        "reason": "reference_compatible" if compatible else "reference_incompatible",
    }


def aggregate_severity(results: list[dict]) -> dict:
    if any(item.get("status") == "failed" for item in results):
        return {"decision": "validation_failed", "severity": "blocking"}
    if any(item.get("status") in {"warning", "incomplete"} for item in results):
        return {"decision": "validation_failed", "severity": "warning"}
    return {"decision": "validated", "severity": "none"}


def validate_resource_limits(*, class_count: int, sample_count: int, policy: dict) -> dict:
    max_classes = int(policy.get("max_classes", 100))
    max_samples = int(policy.get("max_samples", 1_000_000))
    if class_count < 0 or sample_count < 0:
        return {"status": "failed", "reason": "resource_value_invalid"}
    if class_count > max_classes:
        return {"status": "failed", "reason": "class_limit_exceeded", "limit": max_classes}
    if sample_count > max_samples:
        return {"status": "failed", "reason": "sample_limit_exceeded", "limit": max_samples}
    return {"status": "passed", "reason": "resource_limits_passed"}


def validate_calibration_governance(evidence: dict, at: datetime) -> dict:
    if evidence.get("status") not in {"valid", "valid_with_warnings"}:
        return {"status": "failed", "reason": "calibration_not_valid"}
    if not evidence.get("approved_by"):
        return {"status": "failed", "reason": "calibration_not_approved"}
    start, end = evidence.get("valid_from"), evidence.get("valid_to")
    if start is not None and at < start:
        return {"status": "failed", "reason": "calibration_not_yet_valid"}
    if end is not None and at >= end:
        return {"status": "failed", "reason": "calibration_expired"}
    return {"status": "passed", "reason": "calibration_governance_valid"}


def aggregate_statistical_validation(
    rule_results: list[dict], *, abstention_enabled: bool = True
) -> dict:
    aggregate = aggregate_severity(rule_results)
    failed = [item.get("reason") for item in rule_results if item.get("status") == "failed"]
    warnings = [
        item.get("reason")
        for item in rule_results
        if item.get("status") in {"warning", "incomplete"}
    ]
    return {
        "decision": aggregate["decision"],
        "severity": aggregate["severity"],
        "abstain": abstention_enabled and aggregate["decision"] != "validated",
        "blocking_failures": failed,
        "warnings": warnings,
        "rule_count": len(rule_results),
        "checksum": digest({"rules": rule_results, "abstention_enabled": abstention_enabled}),
    }


def validate_calibration_metrics(evidence: dict, policy: dict) -> dict:
    checks = []
    ece = evidence.get("expected_calibration_error")
    if not isinstance(ece, (int, float)) or not math.isfinite(ece) or ece < 0:
        return {"status": "failed", "reason": "calibration_metric_invalid"}
    checks.append(ece <= policy.get("maximum_calibration_error", 1.0))
    if evidence.get("maximum_calibration_error") is not None:
        checks.append(
            evidence["maximum_calibration_error"] <= policy.get("maximum_calibration_error", 1.0)
        )
    for name in ("brier_score", "log_loss"):
        value = evidence.get(name)
        if value is not None and (
            not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0
        ):
            return {"status": "failed", "reason": f"{name}_invalid"}
    return {
        "status": "passed" if all(checks) else "failed",
        "reason": "calibration_metrics_valid" if all(checks) else "calibration_error_exceeded",
    }


def validate_class_support(class_counts: dict[str, int], minimum_support: int = 1) -> dict:
    if not class_counts or any(
        not isinstance(count, int) or count < 0 for count in class_counts.values()
    ):
        return {"status": "failed", "reason": "class_support_invalid"}
    missing = [label for label, count in class_counts.items() if count < minimum_support]
    if missing:
        return {"status": "failed", "reason": "class_support_insufficient", "classes": missing}
    return {"status": "passed", "reason": "class_support_sufficient"}


def replay_manifest(manifest: dict, current: dict) -> dict:
    mismatches = [
        key
        for key in (
            "policy_version",
            "threshold",
            "prediction_checksum",
            "output_contract",
            "implementation_version",
        )
        if manifest.get(key) != current.get(key)
    ]
    return {
        "status": "matched" if not mismatches else "mismatch",
        "mismatches": mismatches,
        "manifest_checksum": digest(manifest),
    }


def lifecycle_identity(parent_identity: str, action: str, reason: str) -> str:
    return digest({"parent_identity": parent_identity, "action": action, "reason": reason})


def run_end_to_end_validation(
    *,
    classification: dict | None = None,
    calibration: dict | None = None,
    regression: dict | None = None,
    interval: dict | None = None,
    reference: dict | None = None,
    class_counts: dict[str, int] | None = None,
    resources: dict | None = None,
    policy: dict | None = None,
    evaluated_at: datetime | None = None,
) -> dict:
    policy = policy or {}
    results: list[dict] = []
    if classification is not None:
        results.append(classification)
    if calibration is not None:
        results.extend(
            [
                validate_calibration_metrics(calibration, policy),
                validate_calibration_governance(calibration, evaluated_at or datetime.now()),
            ]
        )
    if regression is not None:
        results.append(
            validate_regression(regression["value"], regression.get("evidence", {}), policy)
        )
    if interval is not None:
        results.append(validate_prediction_interval(interval["value"], interval))
    if reference is not None:
        results.append(
            validate_reference_distribution(
                reference["value"], reference, float(policy.get("reference_tolerance", 0))
            )
        )
    if class_counts is not None:
        results.append(
            validate_class_support(class_counts, int(policy.get("minimum_class_support", 1)))
        )
    if resources is not None:
        results.append(
            validate_resource_limits(
                class_count=resources["class_count"],
                sample_count=resources["sample_count"],
                policy=policy,
            )
        )
    return aggregate_statistical_validation(
        results, abstention_enabled=bool(policy.get("abstention_enabled", True))
    )
