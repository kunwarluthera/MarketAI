from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class RegistrationPolicy:
    code: str
    version: str
    require_validation_passed: bool = True
    require_package_valid: bool = True
    require_lineage_complete: bool = True
    require_checksums_valid: bool = True


def evaluate_registration(preconditions: dict, policy: RegistrationPolicy) -> dict:
    checks = {
        "validation_passed": preconditions.get("validation_decision") == "validation_passed"
        if policy.require_validation_passed
        else True,
        "package_valid": preconditions.get("package_valid", False)
        if policy.require_package_valid
        else True,
        "lineage_complete": preconditions.get("lineage_complete", False)
        if policy.require_lineage_complete
        else True,
        "checksums_valid": preconditions.get("checksums_valid", False)
        if policy.require_checksums_valid
        else True,
        "no_version_collision": not preconditions.get("version_collision", False),
        "no_duplicate_candidate": not preconditions.get("duplicate_candidate", False),
        "policy_active": preconditions.get("policy_active", True),
    }
    result = {
        "registrable": all(checks.values()),
        "checks": checks,
        "policy_code": policy.code,
        "policy_version": policy.version,
        "research_only": True,
    }
    result["registration_identity"] = sha256(
        json.dumps(result, sort_keys=True).encode()
    ).hexdigest()
    return result
