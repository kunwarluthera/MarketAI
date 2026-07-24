from app.metrics_engine.core import compute


def test_classification_metrics_are_deterministic():
    assert compute("precision", [1, 0, 1], [1, 1, 1])["rounded_value"] == 0.66666667
    assert compute("recall", [1, 0, 1], [1, 1, 1])["rounded_value"] == 1.0
    assert compute("f1", [1, 0, 1], [1, 1, 1])["rounded_value"] == 0.8


def test_r2_is_deterministic():
    assert compute("r2", [1, 2, 3], [1, 2, 3])["rounded_value"] == 1.0
