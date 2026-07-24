from app.prediction_governance.core import aggregate_outcomes


def test_governance_aggregates_existing_outcomes_only():
    valid = {"decision": "validated"}
    assert (
        aggregate_outcomes(
            valid,
            valid,
            {"decision": "safe"},
            policy_enabled=True,
            immutable=True,
            manifests_exist=True,
        )["decision"]
        == "validated"
    )
    assert (
        aggregate_outcomes(
            valid,
            {"decision": "validation_failed"},
            {"decision": "safe"},
            policy_enabled=True,
            immutable=True,
            manifests_exist=True,
        )["decision"]
        == "abstain"
    )
    assert (
        aggregate_outcomes(
            valid,
            valid,
            {"decision": "unsafe"},
            policy_enabled=True,
            immutable=True,
            manifests_exist=True,
        )["decision"]
        == "abstain"
    )
