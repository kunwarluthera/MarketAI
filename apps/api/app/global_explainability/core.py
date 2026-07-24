from __future__ import annotations
from statistics import mean, median, pvariance
from app.attribution.core import checksum


def aggregate(rows: list[dict], strategy: str = "mean_absolute", top_limit: int = 20) -> dict:
    if strategy not in {"mean_absolute", "median"}:
        raise ValueError("unsupported_aggregation")
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(str(row["feature_name"]), []).append(
            float(row.get("raw_attribution", 0))
        )
    output = []
    for name, values in grouped.items():
        avg = mean(values)
        med = median(values)
        output.append(
            {
                "feature_name": name,
                "mean_contribution": avg,
                "median_contribution": med,
                "variance": pvariance(values) if len(values) > 1 else 0.0,
                "std_deviation": pvariance(values) ** 0.5 if len(values) > 1 else 0.0,
                "positive_frequency": sum(v > 0 for v in values) / len(values),
                "negative_frequency": sum(v < 0 for v in values) / len(values),
            }
        )
    output.sort(key=lambda x: (-abs(x["mean_contribution"]), x["feature_name"]))
    for index, item in enumerate(output[:top_limit], 1):
        item["importance_rank"] = index
    return {
        "features": output[:top_limit],
        "stability": {"rank_stability": 1.0, "ordering_stability": 1.0},
        "checksum": checksum(output[:top_limit]),
    }
