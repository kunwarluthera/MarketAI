from __future__ import annotations
from math import sqrt
from app.attribution.core import checksum

METRICS = {
    "accuracy": "classification",
    "precision": "classification",
    "recall": "classification",
    "f1": "classification",
    "mae": "regression",
    "mse": "regression",
    "rmse": "regression",
    "r2": "regression",
}


def compute(metric: str, actual: list[float], predicted: list[float]) -> dict:
    if metric not in METRICS or len(actual) != len(predicted) or not actual:
        raise ValueError("unsupported_metric_or_inputs")
    if metric == "accuracy":
        value = sum(a == p for a, p in zip(actual, predicted)) / len(actual)
    elif metric == "mae":
        value = sum(abs(a - p) for a, p in zip(actual, predicted)) / len(actual)
    elif metric == "mse":
        value = sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual)
    elif metric == "rmse":
        value = sqrt(sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual))
    elif metric in {"precision", "recall", "f1"}:
        tp = sum(a == p == 1 for a, p in zip(actual, predicted))
        fp = sum(a == 0 and p == 1 for a, p in zip(actual, predicted))
        fn = sum(a == 1 and p == 0 for a, p in zip(actual, predicted))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        value = (
            precision
            if metric == "precision"
            else recall
            if metric == "recall"
            else (2 * precision * recall / (precision + recall) if precision + recall else 0.0)
        )
    elif metric == "r2":
        avg = sum(actual) / len(actual)
        denominator = sum((a - avg) ** 2 for a in actual)
        value = (
            1 - sum((a - p) ** 2 for a, p in zip(actual, predicted)) / denominator
            if denominator
            else 0.0
        )
    else:
        raise ValueError("metric_not_implemented")
    return {
        "metric": metric,
        "family": METRICS[metric],
        "raw_value": value,
        "rounded_value": round(value, 8),
        "checksum": checksum({"metric": metric, "value": value}),
    }
