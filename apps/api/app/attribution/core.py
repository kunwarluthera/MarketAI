from __future__ import annotations
from hashlib import sha256
import json


def checksum(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


ALGORITHMS = {
    "Tree SHAP": {"XGBoost", "LightGBM", "RandomForest", "DecisionTree"},
    "Permutation Attribution": {"Linear"},
    "Integrated Gradients placeholder": {"Neural Network"},
    "Kernel SHAP placeholder": set(),
}

ALGORITHM_VERSIONS = {
    "Tree SHAP": "registry-1",
    "Permutation Attribution": "registry-1",
    "Integrated Gradients placeholder": "placeholder-1",
    "Kernel SHAP placeholder": "placeholder-1",
}


class TreeSHAPAlgorithm:
    """Controlled local Tree-SHAP adapter contract.

    The runtime accepts a model-provided contribution vector; it never loads
    artifacts or executes arbitrary model code in the attribution layer.
    """

    name = "Tree SHAP"
    version = "registry-1"

    @staticmethod
    def explain(features: list[dict]) -> list[dict]:
        return attribute(features, normalize=False)


def resolve_algorithm(model_family: str, priority: list[str] | None = None) -> str:
    for algorithm in priority or list(ALGORITHMS):
        if model_family in ALGORITHMS.get(algorithm, set()):
            return algorithm
    raise ValueError("unsupported_model_type")


def resolve_algorithm_contract(model_family: str, priority: list[str] | None = None) -> dict:
    algorithm = resolve_algorithm(model_family, priority)
    return {
        "algorithm": algorithm,
        "version": ALGORITHM_VERSIONS[algorithm],
        "model_family": model_family,
    }


def attribute(features: list[dict], normalize: bool = True, precision: int = 8) -> list[dict]:
    values = [float(item.get("value", 0)) for item in features]
    total = sum(abs(value) for value in values)
    result = []
    for index, (item, raw) in enumerate(zip(features, values)):
        normalized = raw / total if normalize and total else raw
        result.append(
            {
                "feature_name": str(item["name"]),
                "feature_index": index,
                "raw_attribution": round(raw, precision),
                "normalized_attribution": round(normalized, precision),
                "sign": 1 if raw > 0 else -1 if raw < 0 else 0,
                "absolute_magnitude": round(abs(raw), precision),
                "feature_checksum": checksum(item),
            }
        )
    return sorted(result, key=lambda row: (-row["absolute_magnitude"], row["feature_index"]))
