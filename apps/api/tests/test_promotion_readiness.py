from app.promotion_readiness.core import evaluate


def test_readiness_is_deterministic_and_informational():
    evidence = {"evaluation": True, "calibration": True, "benchmark": False}
    first = evaluate(evidence, ["evaluation", "calibration", "benchmark"])
    assert first == evaluate(evidence, ["evaluation", "calibration", "benchmark"])
    assert first["scorecard"]["status"] == "NOT_READY"


def test_complete_evidence_is_ready_for_review():
    result = evaluate({"evaluation": True, "calibration": True}, ["evaluation", "calibration"])
    assert result["scorecard"]["status"] == "READY_FOR_REVIEW"
