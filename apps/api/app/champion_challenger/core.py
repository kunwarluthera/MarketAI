from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class RolePolicy:
    code: str
    version: str
    max_challengers: int = 3
    require_promotion_approval: bool = True


def evaluate_role_eligibility(candidate: dict, policy: RolePolicy) -> dict:
    checks = {
        "approved": candidate.get("promotion_decision") == "approved_for_promotion"
        if policy.require_promotion_approval
        else True,
        "not_expired": not candidate.get("expired", False),
        "not_invalidated": not candidate.get("invalidated", False),
    }
    result = {
        "champion_eligible": all(checks.values()),
        "challenger_eligible": all(checks.values()),
        "checks": checks,
        "policy_code": policy.code,
        "policy_version": policy.version,
        "registry_only": True,
    }
    result["assignment_identity"] = sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result


def validate_assignments(
    champion: str | None, challengers: list[str], policy: RolePolicy
) -> tuple[str, ...]:
    errors = []
    if len(challengers) > policy.max_challengers:
        errors.append("CHALLENGER_LIMIT_EXCEEDED")
    if champion and champion in challengers:
        errors.append("CHAMPION_CANNOT_BE_CHALLENGER")
    if len(set(challengers)) != len(challengers):
        errors.append("DUPLICATE_CHALLENGER")
    return tuple(errors)
