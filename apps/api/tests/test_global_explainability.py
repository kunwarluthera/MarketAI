import pytest
from app.global_explainability.core import aggregate


def test_global_aggregation_is_deterministic_and_ranked():
    rows = [
        {"feature_name": "b", "raw_attribution": 2},
        {"feature_name": "a", "raw_attribution": -4},
    ]
    first = aggregate(rows)
    second = aggregate(rows)
    assert first == second
    assert first["features"][0]["feature_name"] == "a"
    assert first["features"][0]["importance_rank"] == 1


def test_unsupported_aggregation_rejected():
    with pytest.raises(ValueError, match="unsupported_aggregation"):
        aggregate([], "unknown")
