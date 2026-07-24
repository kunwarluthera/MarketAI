import pytest
from app.attribution.core import (
    TreeSHAPAlgorithm,
    attribute,
    resolve_algorithm,
    resolve_algorithm_contract,
)


def test_algorithm_resolution_and_contract():
    assert resolve_algorithm("RandomForest") == "Tree SHAP"
    assert resolve_algorithm_contract("Neural Network")["version"] == "placeholder-1"


def test_deterministic_order_and_normalization():
    result = attribute([{"name": "slow", "value": -2}, {"name": "fast", "value": 4}])
    assert [row["feature_name"] for row in result] == ["fast", "slow"]
    assert result[0]["normalized_attribution"] == 0.66666667
    assert result[1]["sign"] == -1


def test_unknown_model_is_rejected():
    with pytest.raises(ValueError, match="unsupported_model_type"):
        resolve_algorithm("Unknown")


def test_tree_shap_adapter_contract_is_local_and_deterministic():
    first = TreeSHAPAlgorithm.explain([{"name": "x", "value": 2}])
    second = TreeSHAPAlgorithm.explain([{"name": "x", "value": 2}])
    assert first == second
    assert TreeSHAPAlgorithm.name == "Tree SHAP"
