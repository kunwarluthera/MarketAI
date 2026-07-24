from app.validation_decision.core import ValidationPolicy, evaluate_policy


def test_policy_passes_only_when_all_thresholds_pass():
    result = evaluate_policy(
        {"accuracy": 0.8, "completed_folds": 3, "failed_folds": 0, "complete": True},
        ValidationPolicy("default", "1", min_accuracy=0.7, min_completed_folds=2),
    )
    assert result["decision"] == "validation_passed"


def test_incomplete_evidence_requires_review():
    result = evaluate_policy({}, ValidationPolicy("default", "1"))
    assert result["decision"] == "needs_review"
