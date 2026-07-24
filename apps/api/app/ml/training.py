from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class TemporalSplitSpec:
    train_fraction: float = 0.6
    validation_fraction: float = 0.2


def temporal_split(rows: list[dict], spec: TemporalSplitSpec = TemporalSplitSpec()) -> dict:
    ordered = sorted(
        rows, key=lambda row: (row.get("evaluated_at", ""), row.get("row_identity", ""))
    )
    n = len(ordered)
    train_end = int(n * spec.train_fraction)
    validation_end = train_end + int(n * spec.validation_fraction)
    return {
        "train": ordered[:train_end],
        "validation": ordered[train_end:validation_end],
        "test": ordered[validation_end:],
    }


def training_manifest(
    dataset_identity: str, label_spec: str, split: dict, algorithm: str = "baseline_logistic"
) -> dict:
    manifest = {
        "dataset_identity": dataset_identity,
        "label_spec": label_spec,
        "algorithm": algorithm,
        "split_counts": {key: len(value) for key, value in split.items()},
        "research_only": True,
        "inference_enabled": False,
        "trading_connected": False,
    }
    manifest["training_identity"] = sha256(
        json.dumps(manifest, sort_keys=True).encode()
    ).hexdigest()
    return manifest


def evaluate_binary(actual: list[int], probabilities: list[float], threshold: float = 0.5) -> dict:
    if len(actual) != len(probabilities) or not actual:
        raise ValueError("Evaluation inputs must be non-empty and aligned")
    predictions = [int(value >= threshold) for value in probabilities]
    accuracy = sum(a == p for a, p in zip(actual, predictions)) / len(actual)
    brier = sum((p - a) ** 2 for a, p in zip(actual, probabilities)) / len(actual)
    return {
        "sample_count": len(actual),
        "accuracy": accuracy,
        "brier_score": brier,
        "threshold": threshold,
        "research_only": True,
    }


def fit_majority_baseline(labels: list[int]) -> dict:
    if not labels or any(value not in (0, 1) for value in labels):
        raise ValueError("Binary labels are required")
    artifact = {
        "algorithm": "majority_rate_baseline",
        "positive_rate": sum(labels) / len(labels),
        "sample_count": len(labels),
        "inference_enabled": False,
        "research_only": True,
    }
    artifact["artifact_identity"] = sha256(
        json.dumps(artifact, sort_keys=True).encode()
    ).hexdigest()
    return artifact
