import pytest
from app.regime_evaluation.core import evaluate


def test_regime_segment_evaluation_is_deterministic():
    result = evaluate({"Bull": [1.0, 2.0], "Bear": [3.0, 5.0]})
    assert result == evaluate({"Bull": [1.0, 2.0], "Bear": [3.0, 5.0]})
    assert result["coverage"]["group_count"] == 2


def test_minimum_sample_rejected():
    with pytest.raises(ValueError, match="minimum_samples"):
        evaluate({"Bull": []}, minimum_samples=1)
