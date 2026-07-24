from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json


SCHEMA_VERSION = "2.6.1"
REQUIRED_SECTIONS = (
    "market_context",
    "features",
    "evidence",
    "external_intelligence",
    "opportunity",
    "lineage",
)


@dataclass(frozen=True)
class ResearchSnapshotInput:
    instrument_id: str
    evaluated_at: datetime
    market_context: dict
    features: dict
    evidence: dict
    external_intelligence: dict
    opportunity: dict
    lineage: dict


def build_snapshot(inputs: ResearchSnapshotInput) -> dict:
    """Build a deterministic, source-preserving downstream research contract."""
    payload = {
        "schema_version": SCHEMA_VERSION,
        "instrument_id": inputs.instrument_id,
        "evaluated_at": inputs.evaluated_at.isoformat(),
        "market_context": inputs.market_context,
        "features": inputs.features,
        "evidence": inputs.evidence,
        "external_intelligence": inputs.external_intelligence,
        "opportunity": inputs.opportunity,
        "lineage": inputs.lineage,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    payload["snapshot_identity"] = sha256(canonical.encode()).hexdigest()
    return payload


def validate_snapshot(payload: dict) -> tuple[str, ...]:
    """Return deterministic completeness errors without mutating the snapshot."""
    errors = []
    for section in REQUIRED_SECTIONS:
        if section not in payload:
            errors.append(f"MISSING_{section.upper()}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("SCHEMA_VERSION_MISMATCH")
    if not payload.get("snapshot_identity"):
        errors.append("MISSING_SNAPSHOT_IDENTITY")
    return tuple(errors)
