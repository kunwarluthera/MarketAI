from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class PromotionPolicy:
    code: str
    version: str
    required_validation: str = "validation_passed"
    required_approvals: int = 1
    require_distinct_approvers: bool = True


def evaluate_eligibility(candidate: dict, policy: PromotionPolicy) -> dict:
    checks = {
        "candidate_registered": candidate.get("status") == "registered",
        "validation_satisfied": candidate.get("validation_decision") == policy.required_validation,
        "not_expired": not candidate.get("expired", False),
        "not_cancelled": not candidate.get("cancelled", False),
    }
    result = {
        "decision": "promotion_eligible" if all(checks.values()) else "promotion_ineligible",
        "policy_code": policy.code,
        "policy_version": policy.version,
        "checks": checks,
        "research_only": True,
    }
    result["eligibility_identity"] = sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result


def evaluate_quorum(approvers: list[str], policy: PromotionPolicy) -> dict:
    unique = set(approvers)
    sufficient = (
        len(unique) >= policy.required_approvals
        if policy.require_distinct_approvers
        else len(approvers) >= policy.required_approvals
    )
    return {
        "quorum_met": sufficient,
        "approval_count": len(approvers),
        "distinct_approver_count": len(unique),
        "required_approvals": policy.required_approvals,
    }
