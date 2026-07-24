"""Deterministic cross-layer analysis for Layer 2.5 research inputs."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ResearchInput:
    instrument_id: str
    evaluated_at: datetime
    technical_items: tuple[dict, ...] = ()
    external_items: tuple[dict, ...] = ()
    technical_ready: bool = True
    external_ready: bool = True
    active_instrument: bool = True


@dataclass(frozen=True)
class AnalysisResult:
    supports: tuple[dict, ...]
    conflicts: tuple[dict, ...]
    missing_required: tuple[str, ...]
    missing_optional: tuple[str, ...]
    stale_inputs: tuple[str, ...]
    readiness: str
    blockers: tuple[str, ...]


def assemble_as_of(
    instrument_id: str,
    evaluated_at: datetime,
    technical: list[dict],
    external: list[dict],
    *,
    technical_ready: bool = True,
    external_ready: bool = True,
    active_instrument: bool = True,
) -> ResearchInput:
    """Keep only records available at the explicit evaluation timestamp."""
    bounded_technical = tuple(
        x for x in technical if x.get("evaluated_at", evaluated_at) <= evaluated_at
    )
    bounded_external = tuple(
        x for x in external if x.get("evaluated_at", evaluated_at) <= evaluated_at
    )
    return ResearchInput(
        instrument_id,
        evaluated_at,
        bounded_technical,
        bounded_external,
        technical_ready,
        external_ready,
        active_instrument,
    )


def analyze(inputs: ResearchInput) -> AnalysisResult:
    tech = {x.get("direction") for x in inputs.technical_items}
    ext = {x.get("impact") for x in inputs.external_items}
    supports: list[dict] = []
    conflicts: list[dict] = []
    if tech & ext and ("positive" in tech & ext or "negative" in tech & ext):
        supports.append({"relationship_code": "CROSS_LAYER_ALIGNMENT", "strength": "medium"})
    if ("positive" in tech and "negative" in ext) or ("negative" in tech and "positive" in ext):
        conflicts.append({"conflict_code": "TECHNICAL_EXTERNAL_CONFLICT", "severity": "high"})
    missing_required = []
    blockers = []
    if not inputs.technical_ready:
        missing_required.append("technical_readiness")
        blockers.append("TECHNICAL_DATA_NOT_READY")
    if not inputs.active_instrument:
        blockers.append("INACTIVE_INSTRUMENT")
    if not inputs.external_ready:
        blockers.append("external_readiness")
    missing_optional = ["external_event"] if not inputs.external_items else []
    stale = tuple(
        x.get("id", "unknown")
        for x in (*inputs.technical_items, *inputs.external_items)
        if x.get("stale") is True
    )
    if stale:
        blockers.append("STALE_INPUT")
    readiness = (
        "not_ready" if blockers else "degraded" if conflicts or missing_optional else "ready"
    )
    return AnalysisResult(
        tuple(supports),
        tuple(conflicts),
        tuple(missing_required),
        tuple(missing_optional),
        stale,
        readiness,
        tuple(dict.fromkeys(blockers)),
    )
