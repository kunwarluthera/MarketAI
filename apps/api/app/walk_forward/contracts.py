from dataclasses import dataclass
from hashlib import sha256
import json


@dataclass(frozen=True)
class TrainingRecipe:
    code: str
    version: str
    dataset_identity: str
    label_spec: str
    algorithm: str
    hyperparameters: dict


@dataclass(frozen=True)
class WalkForwardSpec:
    code: str
    version: str
    train_observations: int
    validation_observations: int
    test_observations: int
    step_observations: int
    mode: str = "rolling"


def validation_identity(recipe: TrainingRecipe, spec: WalkForwardSpec) -> str:
    payload = {"recipe": recipe.__dict__, "spec": spec.__dict__}
    return sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def fold_identity(validation_id: str, fold_number: int) -> str:
    return sha256(f"{validation_id}:{fold_number}".encode()).hexdigest()


def generate_folds(rows: list[dict], spec: WalkForwardSpec, validation_id: str) -> list[dict]:
    ordered = sorted(
        rows, key=lambda row: (row.get("evaluated_at", ""), row.get("row_identity", ""))
    )
    folds = []
    start = 0
    number = 1
    width = spec.train_observations + spec.validation_observations + spec.test_observations
    while start + width <= len(ordered):
        train_end = start + spec.train_observations
        validation_end = train_end + spec.validation_observations
        test_end = validation_end + spec.test_observations
        folds.append(
            {
                "fold_number": number,
                "fold_identity": fold_identity(validation_id, number),
                "train": ordered[start:train_end],
                "validation": ordered[train_end:validation_end],
                "test": ordered[validation_end:test_end],
            }
        )
        start += spec.step_observations
        number += 1
    return folds


def execute_baseline_folds(folds: list[dict], label_key: str = "label") -> list[dict]:
    """Train a fresh prior-rate baseline for each fold and evaluate its test rows."""
    results = []
    for fold in folds:
        labels = [row[label_key] for row in fold["train"] if row.get(label_key) in (0, 1)]
        if not labels:
            results.append(
                {
                    "fold_number": fold["fold_number"],
                    "fold_identity": fold["fold_identity"],
                    "status": "insufficient_data",
                }
            )
            continue
        rate = sum(labels) / len(labels)
        test = [row for row in fold["test"] if row.get(label_key) in (0, 1)]
        accuracy = sum((1 if rate >= 0.5 else 0) == row[label_key] for row in test) / max(
            1, len(test)
        )
        results.append(
            {
                "fold_number": fold["fold_number"],
                "fold_identity": fold["fold_identity"],
                "status": "completed",
                "training_positive_rate": rate,
                "test_count": len(test),
                "accuracy": accuracy,
                "fresh_model": True,
            }
        )
    return results
