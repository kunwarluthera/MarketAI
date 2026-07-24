from dataclasses import dataclass
from hashlib import sha256
import json
import math


@dataclass(frozen=True)
class PredictionPolicy:
    code: str
    version: str
    max_rows: int = 10_000
    require_historical: bool = True


def validate_request(rows: list[dict], policy: PredictionPolicy) -> None:
    if len(rows) > policy.max_rows:
        raise ValueError("Offline request exceeds row limit")
    if policy.require_historical and any(row.get("is_live", False) for row in rows):
        raise ValueError("Live data is not allowed")


def normalize_output(value: object) -> dict:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return {"output_type": "regression", "value": float(value)}
    if isinstance(value, dict) and "class" in value:
        probability = value.get("probability")
        if probability is not None and (
            not isinstance(probability, (int, float)) or not 0 <= probability <= 1
        ):
            raise ValueError("Invalid probability")
        return {
            "output_type": "classification",
            "class": value["class"],
            "probability": probability,
        }
    raise ValueError("Unsupported prediction output")


def prediction_identity(request_id: str, model_version: str, outputs: list[dict]) -> str:
    return sha256(
        json.dumps(
            {"request_id": request_id, "model_version": model_version, "outputs": outputs},
            sort_keys=True,
        ).encode()
    ).hexdigest()
