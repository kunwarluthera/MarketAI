from app.promotion.core import PromotionPolicy, evaluate_eligibility, evaluate_quorum


def test_eligibility_is_policy_driven():
    result = evaluate_eligibility(
        {"status": "registered", "validation_decision": "validation_passed"},
        PromotionPolicy("default", "1"),
    )
    assert result["decision"] == "promotion_eligible"


def test_quorum_requires_distinct_approvers():
    assert (
        evaluate_quorum(
            ["reviewer", "reviewer"], PromotionPolicy("default", "1", required_approvals=2)
        )["quorum_met"]
        is False
    )
