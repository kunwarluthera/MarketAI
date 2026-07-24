from dataclasses import dataclass
from hashlib import sha256
import json


LABEL_SCHEMA_VERSION = "3.2.1"


@dataclass(frozen=True)
class OutcomeSpec:
    outcome_code: str
    outcome_version: str
    horizon_bars: int
    interval_minutes: int
    price_field: str = "close"


@dataclass(frozen=True)
class LabelSpec:
    label_code: str
    label_version: str
    outcome_code: str
    positive_threshold: float
    negative_threshold: float


def calculate_raw_outcome(feature_row: dict, future_bars: list[dict], spec: OutcomeSpec) -> dict:
    """Calculate future ground truth without modifying or augmenting features."""
    if len(future_bars) < spec.horizon_bars:
        return {
            "status": "immature",
            "outcome_code": spec.outcome_code,
            "outcome_version": spec.outcome_version,
        }
    start = feature_row.get("features", {}).get(spec.price_field)
    end = future_bars[spec.horizon_bars - 1].get(spec.price_field)
    if start is None or end is None or start <= 0:
        return {
            "status": "invalid",
            "outcome_code": spec.outcome_code,
            "outcome_version": spec.outcome_version,
        }
    return {
        "status": "mature",
        "outcome_code": spec.outcome_code,
        "outcome_version": spec.outcome_version,
        "feature_cutoff_at": feature_row.get("evaluated_at"),
        "observation_end_at": future_bars[spec.horizon_bars - 1].get("ended_at"),
        "return": (end - start) / start,
    }


def derive_label(raw_outcome: dict, spec: LabelSpec) -> dict:
    if raw_outcome.get("status") != "mature":
        return {
            "status": raw_outcome.get("status", "unavailable"),
            "label_code": spec.label_code,
            "label_version": spec.label_version,
        }
    value = raw_outcome["return"]
    label = (
        "positive"
        if value >= spec.positive_threshold
        else "negative"
        if value <= spec.negative_threshold
        else "neutral"
    )
    result = {
        "status": "mature",
        "label_code": spec.label_code,
        "label_version": spec.label_version,
        "outcome": value,
        "label": label,
        "available_at": raw_outcome.get("observation_end_at"),
    }
    result["label_identity"] = sha256(
        json.dumps(result, sort_keys=True, default=str).encode()
    ).hexdigest()
    return result


def label_quality(records: list[dict]) -> dict:
    mature = sum(1 for record in records if record.get("status") == "mature")
    return {
        "record_count": len(records),
        "mature_count": mature,
        "immature_count": len(records) - mature,
        "maturity_rate": mature / max(1, len(records)),
        "contains_predictions": False,
    }


def compare_labels(left: list[dict], right: list[dict]) -> dict:
    a = {record.get("label_identity") for record in left}
    b = {record.get("label_identity") for record in right}
    return {"added": sorted(b - a), "removed": sorted(a - b), "unchanged": a == b}
