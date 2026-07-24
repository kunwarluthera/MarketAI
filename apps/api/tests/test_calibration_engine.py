from app.calibration_engine.core import calibrate


def test_calibration_metrics_and_bins_are_deterministic():
    result = calibrate([0.1, 0.9, 0.8, 0.2], [0, 1, 1, 0], bins=2)
    assert result == calibrate([0.1, 0.9, 0.8, 0.2], [0, 1, 1, 0], bins=2)
    assert {item["metric"] for item in result["metrics"]} == {
        "brier_score",
        "log_loss",
        "ece",
        "mce",
    }
    assert len(result["bins"]) == 2
