import math

from app.statistical_validation.core import (
    StatisticalPolicy,
    aggregate_severity,
    classification_statistics,
    digest,
    validate_calibration_evidence,
    validate_calibration_metrics,
    validate_class_support,
    validate_prediction_interval,
    validate_probabilities,
    validate_reference_distribution,
    validate_regression,
    validate_resource_limits,
    run_end_to_end_validation,
    aggregate_statistical_validation,
    lifecycle_identity,
    replay_manifest,
)


def test_aggregate_statistical_validation_is_deterministic():
    result = aggregate_statistical_validation(
        [
            {"status": "passed", "reason": "confidence"},
            {"status": "warning", "reason": "calibration"},
        ]
    )
    assert result["decision"] == "validation_failed"
    assert result["abstain"] is True
    assert result["warnings"] == ["calibration"]


def test_end_to_end_orchestration_covers_governed_groups():
    result = run_end_to_end_validation(
        classification={"status": "passed", "reason": "confidence"},
        calibration={"expected_calibration_error": 0.1, "status": "valid", "approved_by": "qa"},
        regression={"value": 2.0, "evidence": {"residual": 0.1}},
        interval={"value": 2.0, "lower": 1.0, "upper": 3.0},
        reference={"value": 2.0, "lower": 1.0, "upper": 3.0},
        class_counts={"a": 4, "b": 4},
        resources={"class_count": 2, "sample_count": 8},
        policy={
            "maximum_calibration_error": 0.2,
            "minimum_class_support": 2,
            "abstention_enabled": True,
        },
    )
    assert result["decision"] == "validated"
    assert result["rule_count"] == 8


def test_resource_limits_reject_oversized_inputs():
    policy = {"max_classes": 5, "max_samples": 20}
    assert (
        validate_resource_limits(class_count=3, sample_count=10, policy=policy)["status"]
        == "passed"
    )
    assert (
        validate_resource_limits(class_count=6, sample_count=10, policy=policy)["reason"]
        == "class_limit_exceeded"
    )
    assert (
        validate_resource_limits(class_count=3, sample_count=21, policy=policy)["reason"]
        == "sample_limit_exceeded"
    )


def test_probability_validation_is_deterministic():
    assert validate_probabilities(["no", "yes"], [0.25, 0.75])["status"] == "passed"
    assert validate_probabilities(["no", "yes"], [0.2, 0.2])["reason"] == "probability_sum_invalid"


def test_classification_margin_and_entropy():
    result = classification_statistics(
        ["no", "yes"], [0.2, 0.8], StatisticalPolicy(minimum_confidence=0.7, maximum_entropy=1.0)
    )
    assert result["decision"] == "validated"
    assert result["predicted_class"] == "yes"
    assert math.isclose(result["margin"], 0.6)
    assert 0 <= result["normalized_entropy"] <= 1


def test_invalid_probability_and_abstention():
    result = classification_statistics(
        ["a", "b"], [0.5, 0.5], StatisticalPolicy(minimum_confidence=0.9)
    )
    assert result["decision"] == "validation_failed"
    assert digest(result) == digest(result)


def test_calibration_regression_interval_reference_and_severity():
    evidence = {
        "model_version": "m1",
        "output_contract": "c1",
        "sample_count": 20,
        "expected_calibration_error": 0.1,
        "evidence_checksum": "x",
        "status": "valid",
    }
    assert (
        validate_calibration_evidence(
            evidence, {"minimum_sample_support": 10, "maximum_calibration_error": 0.2}
        )["status"]
        == "passed"
    )
    assert (
        validate_regression(2.0, {"residual": 0.1}, {"lower_bound": 0, "upper_bound": 3})["status"]
        == "passed"
    )
    assert validate_prediction_interval(2.0, {"lower": 1, "upper": 3})["status"] == "passed"
    assert validate_reference_distribution(2.0, {"lower": 1, "upper": 3})["status"] == "passed"
    assert aggregate_severity([{"status": "warning"}])["severity"] == "warning"


def test_class_support_replay_and_lifecycle_identity():
    assert validate_class_support({"a": 3, "b": 2}, 2)["status"] == "passed"
    assert validate_class_support({"a": 1, "b": 2}, 2)["reason"] == "class_support_insufficient"
    manifest = {
        "policy_version": "1",
        "threshold": 0.5,
        "prediction_checksum": "p",
        "output_contract": "c",
        "implementation_version": "1",
    }
    assert replay_manifest(manifest, dict(manifest))["status"] == "matched"
    assert replay_manifest(manifest, {**manifest, "threshold": 0.6})["mismatches"] == ["threshold"]
    assert lifecycle_identity("parent", "invalidate", "reason") == lifecycle_identity(
        "parent", "invalidate", "reason"
    )


def test_replay_and_lifecycle_identities_are_immutable_and_deterministic():
    manifest = {"policy_version": "1", "threshold": 0.5}
    first = replay_manifest(manifest, dict(manifest))
    second = replay_manifest(manifest, dict(manifest))
    assert first == second
    assert first["manifest_checksum"] == digest(manifest)
    identity = lifecycle_identity("request-1", "invalidate", "operator error")
    assert identity == lifecycle_identity("request-1", "invalidate", "operator error")
    assert identity != lifecycle_identity("request-1", "supersede", "operator error")


def test_calibration_metric_bounds_and_structural_failures():
    base = {
        "expected_calibration_error": 0.1,
        "maximum_calibration_error": 0.15,
        "brier_score": 0.2,
        "log_loss": 0.3,
    }
    assert (
        validate_calibration_metrics(base, {"maximum_calibration_error": 0.2})["status"] == "passed"
    )
    assert (
        validate_calibration_metrics(
            {**base, "expected_calibration_error": 0.4}, {"maximum_calibration_error": 0.2}
        )["status"]
        == "failed"
    )
    assert validate_probabilities([], [1.0])["reason"] == "probability_structure_invalid"
    assert validate_prediction_interval(2, {"lower": 3, "upper": 1})["status"] == "failed"
    assert (
        validate_reference_distribution(10, {"lower": 1, "upper": 2})["reason"]
        == "reference_incompatible"
    )
