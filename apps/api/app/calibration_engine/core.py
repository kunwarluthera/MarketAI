from __future__ import annotations
from math import log
from app.attribution.core import checksum


def calibrate(probabilities: list[float], outcomes: list[int], bins: int = 10) -> dict:
    if (
        len(probabilities) != len(outcomes)
        or not probabilities
        or any(p < 0 or p > 1 for p in probabilities)
    ):
        raise ValueError("invalid_probability_inputs")
    grouped = []
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        selected = [
            (p, y)
            for p, y in zip(probabilities, outcomes)
            if lower <= p < upper or (index == bins - 1 and p == upper)
        ]
        if selected:
            grouped.append(
                {
                    "bin_id": index,
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "prediction_count": len(selected),
                    "average_confidence": sum(p for p, _ in selected) / len(selected),
                    "observed_frequency": sum(y for _, y in selected) / len(selected),
                }
            )
    brier = sum((p - y) ** 2 for p, y in zip(probabilities, outcomes)) / len(probabilities)
    logloss = -sum(
        y * log(max(p, 1e-15)) + (1 - y) * log(max(1 - p, 1e-15))
        for p, y in zip(probabilities, outcomes)
    ) / len(probabilities)
    errors = [abs(row["average_confidence"] - row["observed_frequency"]) for row in grouped]
    ece = sum(error * row["prediction_count"] for error, row in zip(errors, grouped)) / len(
        probabilities
    )
    return {
        "bins": grouped,
        "metrics": [
            {"metric": "brier_score", "value": brier},
            {"metric": "log_loss", "value": logloss},
            {"metric": "ece", "value": ece},
            {"metric": "mce", "value": max(errors, default=0.0)},
        ],
        "checksum": checksum({"bins": grouped, "brier": brier, "logloss": logloss}),
    }
