import pytest
from app.offline_prediction.core import (
    PredictionPolicy,
    normalize_output,
    prediction_identity,
    validate_request,
)


def test_offline_policy_rejects_live_rows_and_normalizes_outputs():
    with pytest.raises(ValueError):
        validate_request([{"is_live": True}], PredictionPolicy("offline", "1"))
    assert (
        normalize_output({"class": "positive", "probability": 0.8})["output_type"]
        == "classification"
    )


def test_prediction_identity_is_reproducible():
    output = normalize_output(1.2)
    assert prediction_identity("r", "v", [output]) == prediction_identity("r", "v", [output])
