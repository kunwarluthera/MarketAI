from app.prediction_validation.core import assess_eligibility, checksum, execute_rules


def _prediction(**overrides):
    value = {
        "status": "completed",
        "output_validated": True,
        "checksum_valid": True,
        "model_status": "approved",
    }
    value.update(overrides)
    return value


def test_valid_prediction_is_eligible_and_all_rules_pass():
    outcomes = execute_rules(_prediction(), {"enabled": True}, {"checksum_valid": True})
    assert (
        assess_eligibility(_prediction(), {"enabled": True}, {"checksum_valid": True}).status
        == "eligible"
    )
    assert all(item["passed"] for item in outcomes)


def test_missing_manifest_is_ineligible():
    result = assess_eligibility(_prediction(), {"enabled": True}, None)
    assert (result.status, result.reason) == ("ineligible", "missing_manifest")


def test_invalidated_and_superseded_predictions_are_rejected():
    assert (
        assess_eligibility(_prediction(invalidated=True), {"enabled": True}, {}).status
        == "prediction_invalidated"
    )
    assert (
        assess_eligibility(_prediction(superseded=True), {"enabled": True}, {}).status
        == "prediction_superseded"
    )


def test_disabled_policy_is_rejected():
    assert assess_eligibility(_prediction(), {"enabled": False}, {}).status == "policy_disabled"


def test_checksums_are_canonical_and_deterministic():
    assert checksum({"b": 2, "a": 1}) == checksum({"a": 1, "b": 2})
