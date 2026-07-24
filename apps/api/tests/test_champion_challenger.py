from app.champion_challenger.core import RolePolicy, evaluate_role_eligibility, validate_assignments


def test_role_eligibility_requires_approved_promotion():
    result = evaluate_role_eligibility(
        {"promotion_decision": "approved_for_promotion"}, RolePolicy("default", "1")
    )
    assert result["champion_eligible"] is True
    assert result["registry_only"] is True


def test_assignments_enforce_bounds_and_separation():
    assert "CHALLENGER_LIMIT_EXCEEDED" in validate_assignments(
        "champion", ["a", "b", "c", "d"], RolePolicy("default", "1")
    )
    assert "CHAMPION_CANNOT_BE_CHALLENGER" in validate_assignments(
        "a", ["a"], RolePolicy("default", "1")
    )
