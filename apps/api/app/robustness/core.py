from hashlib import sha256
import json
from statistics import mean


def classify_historical_regime(context: dict, version: str = "1") -> dict:
    """Classify supplied historical context deterministically; never reads live data."""
    volatility = context.get("volatility")
    liquidity = context.get("relative_volume")
    if volatility is None or liquidity is None:
        regime = "insufficient_evidence"
    elif volatility >= 0.03:
        regime = "high_volatility"
    elif liquidity < 0.5:
        regime = "low_liquidity"
    else:
        regime = "normal_conditions"
    return {
        "regime": regime,
        "definition_version": version,
        "historical_only": True,
        "source_context": context,
    }


def robustness_summary(
    folds: list[dict], regime_key: str = "regime", metric: str = "accuracy"
) -> dict:
    groups: dict[str, list[float]] = {}
    for fold in folds:
        if fold.get("status") == "completed" and isinstance(fold.get(metric), (int, float)):
            groups.setdefault(fold.get(regime_key, "unknown"), []).append(fold[metric])
    summary = {
        key: {"fold_count": len(values), "mean": mean(values)}
        for key, values in sorted(groups.items())
    }
    result = {"metric": metric, "regimes": summary, "historical_only": True}
    result["summary_identity"] = sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result
