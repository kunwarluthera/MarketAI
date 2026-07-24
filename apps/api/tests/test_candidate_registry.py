from app.candidate_registry.core import RegistrationPolicy, evaluate_registration


def test_candidate_registration_requires_all_preconditions():
    result = evaluate_registration(
        {
            "validation_decision": "validation_passed",
            "package_valid": True,
            "lineage_complete": True,
            "checksums_valid": True,
        },
        RegistrationPolicy("default", "1"),
    )
    assert result["registrable"] is True


def test_failed_validation_blocks_registration():
    result = evaluate_registration(
        {
            "validation_decision": "needs_review",
            "package_valid": True,
            "lineage_complete": True,
            "checksums_valid": True,
        },
        RegistrationPolicy("default", "1"),
    )
    assert result["registrable"] is False
