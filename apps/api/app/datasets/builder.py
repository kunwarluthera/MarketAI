from dataclasses import dataclass
from hashlib import sha256
import json


DATASET_SCHEMA_VERSION = "3.1.1"


@dataclass(frozen=True)
class DatasetSpec:
    dataset_code: str
    dataset_version: str
    feature_paths: tuple[str, ...]
    categorical_paths: tuple[str, ...] = ()


def _path(payload: dict, path: str):
    value = payload
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def build_feature_row(snapshot: dict, spec: DatasetSpec) -> dict:
    """Extract only declared fields from one immutable Layer 2.6 snapshot."""
    if snapshot.get("schema_version") is None:
        raise ValueError("Snapshot schema version is required")
    features = {path: _path(snapshot, path) for path in spec.feature_paths}
    categoricals = {path: _path(snapshot, path) for path in spec.categorical_paths}
    row = {
        "dataset_schema_version": DATASET_SCHEMA_VERSION,
        "dataset_code": spec.dataset_code,
        "dataset_version": spec.dataset_version,
        "snapshot_identity": snapshot.get("snapshot_identity"),
        "instrument_id": snapshot.get("instrument_id"),
        "evaluated_at": snapshot.get("evaluated_at"),
        "features": features,
        "categoricals": categoricals,
        "missing_fields": tuple(
            sorted([key for key, value in {**features, **categoricals}.items() if value is None])
        ),
    }
    canonical = json.dumps(row, sort_keys=True, default=str, separators=(",", ":"))
    row["row_identity"] = sha256(canonical.encode()).hexdigest()
    return row


def build_dataset(snapshots: list[dict], spec: DatasetSpec) -> dict:
    rows = [build_feature_row(snapshot, spec) for snapshot in snapshots]
    identity = sha256(
        json.dumps([row["row_identity"] for row in rows], sort_keys=True).encode()
    ).hexdigest()
    return {
        "dataset_schema_version": DATASET_SCHEMA_VERSION,
        "dataset_code": spec.dataset_code,
        "dataset_version": spec.dataset_version,
        "dataset_identity": identity,
        "row_count": len(rows),
        "rows": rows,
        "contains_labels": False,
    }


def dataset_quality(dataset: dict) -> dict:
    rows = dataset.get("rows", [])
    missing = sum(len(row.get("missing_fields", ())) for row in rows)
    return {
        "row_count": len(rows),
        "missing_value_count": missing,
        "missingness_rate": missing / max(1, len(rows)),
        "contains_labels": bool(dataset.get("contains_labels")),
        "quality_status": "degraded" if missing else "ready",
    }


def compare_datasets(left: dict, right: dict) -> dict:
    a = {row["row_identity"] for row in left.get("rows", [])}
    b = {row["row_identity"] for row in right.get("rows", [])}
    return {
        "left_identity": left.get("dataset_identity"),
        "right_identity": right.get("dataset_identity"),
        "added_rows": sorted(b - a),
        "removed_rows": sorted(a - b),
        "unchanged": left.get("dataset_identity") == right.get("dataset_identity"),
    }


def export_dataset(dataset: dict) -> str:
    return json.dumps(dataset, sort_keys=True, separators=(",", ":"), default=str)
