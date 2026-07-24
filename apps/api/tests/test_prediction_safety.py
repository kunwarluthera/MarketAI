from app.prediction_safety.core import (
    aggregate_safety_decision,
    checksum,
    run_safety_gates,
    safety_eligibility,
    validate_input_integrity,
    validate_ood_bounds,
    validate_regime_compatibility,
)


def test_safety_eligibility_requires_statistical_validation_and_manifests():
    assert (
        safety_eligibility(
            statistical_decision="validated",
            prediction_immutable=True,
            prediction_manifest=True,
            statistical_manifest=True,
            model_approved=True,
            policy_enabled=True,
        )["status"]
        == "eligible"
    )
    assert (
        safety_eligibility(
            statistical_decision="validation_failed",
            prediction_immutable=True,
            prediction_manifest=True,
            statistical_manifest=True,
            model_approved=True,
            policy_enabled=True,
        )["reason"]
        == "missing_statistical_validation"
    )


def test_input_integrity_is_deterministic():
    names = ["ema", "rsi"]
    values = [1.0, 2.0]
    digest = checksum({"schema_version": "1", "feature_names": names, "features": values})
    assert validate_input_integrity(values, names, names, digest, "1", "1")["status"] == "passed"
    assert (
        validate_input_integrity(values, names, names, "bad", "1", "1")["reason"]
        == "feature_checksum_invalid"
    )


def test_ood_and_regime_gates_are_deterministic():
    bounds = {"ema": {"lower": 0.0, "upper": 10.0}}
    assert validate_ood_bounds({"ema": 5.0}, bounds)["status"] == "passed"
    assert validate_ood_bounds({"ema": 11.0}, bounds)["reason"] == "ood_bounds_failed"
    assert validate_regime_compatibility("trending", ["trending", "sideways"])["status"] == "passed"
    assert (
        validate_regime_compatibility("volatile", ["trending"])["reason"] == "regime_incompatible"
    )


def test_safety_orchestrator_abstains_on_any_blocking_gate():
    passed = {"status": "passed", "reason": "ok"}
    result = run_safety_gates(
        eligibility=passed,
        integrity=passed,
        ood={"status": "failed", "reason": "ood_bounds_failed"},
        regime=passed,
    )
    assert result["decision"] == "unsafe"
    assert result["abstain"] is True
    assert aggregate_safety_decision([passed, passed])["decision"] == "safe"
