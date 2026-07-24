import pytest
from app.benchmark_engine.core import compare


def test_benchmark_comparison_is_deterministic():
    first = compare({"accuracy": 0.8}, {"accuracy": 0.9}, "dataset-v1", "dataset-v1")
    assert first == compare({"accuracy": 0.8}, {"accuracy": 0.9}, "dataset-v1", "dataset-v1")
    assert first["deltas"]["accuracy"] == pytest.approx(0.1)


def test_incompatible_datasets_rejected():
    with pytest.raises(ValueError, match="dataset_incompatible"):
        compare({}, {}, "left", "right")
