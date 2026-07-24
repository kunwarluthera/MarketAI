from hashlib import sha256
import json
from statistics import mean, pstdev


def aggregate_metric(folds: list[dict], metric: str) -> dict:
    values = [
        fold[metric]
        for fold in folds
        if fold.get("status") == "completed" and isinstance(fold.get(metric), (int, float))
    ]
    if not values:
        return {"metric": metric, "status": "unavailable", "fold_count": 0}
    weights = [
        fold.get("test_count", 1)
        for fold in folds
        if fold.get("status") == "completed" and isinstance(fold.get(metric), (int, float))
    ]
    weighted = sum(value * weight for value, weight in zip(values, weights)) / sum(weights)
    best = max(folds, key=lambda fold: fold.get(metric, float("-inf")))
    worst = min(folds, key=lambda fold: fold.get(metric, float("inf")))
    return {
        "metric": metric,
        "status": "available",
        "fold_count": len(values),
        "unweighted_mean": mean(values),
        "support_weighted_mean": weighted,
        "dispersion": pstdev(values) if len(values) > 1 else 0.0,
        "best_fold": best.get("fold_number"),
        "worst_fold": worst.get("fold_number"),
    }


def build_report(
    validation_id: str, folds: list[dict], metrics: tuple[str, ...] = ("accuracy",)
) -> dict:
    report = {
        "validation_id": validation_id,
        "metrics": {metric: aggregate_metric(folds, metric) for metric in metrics},
        "fold_count": len(folds),
        "research_only": True,
    }
    report["report_identity"] = sha256(
        json.dumps(report, sort_keys=True, default=str).encode()
    ).hexdigest()
    return report
