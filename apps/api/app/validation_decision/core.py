from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class ValidationPolicy:
    code: str
    version: str
    min_accuracy: float | None = None
    max_brier: float | None = None
    min_completed_folds: int = 1
    max_failed_folds: int = 0


def evaluate_policy(metrics: dict, policy: ValidationPolicy) -> dict:
    checks = []
    if policy.min_accuracy is not None:
        checks.append(
            metrics.get("accuracy") is not None and metrics["accuracy"] >= policy.min_accuracy
        )
    if policy.max_brier is not None:
        checks.append(
            metrics.get("brier_score") is not None and metrics["brier_score"] <= policy.max_brier
        )
    checks.append(metrics.get("completed_folds", 0) >= policy.min_completed_folds)
    checks.append(metrics.get("failed_folds", 0) <= policy.max_failed_folds)
    decision = (
        "validation_passed"
        if checks and all(checks)
        else "validation_failed"
        if metrics.get("complete", False)
        else "needs_review"
    )
    result = {
        "decision": decision,
        "policy_code": policy.code,
        "policy_version": policy.version,
        "checks": checks,
        "research_only": True,
    }
    result["decision_identity"] = sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result
