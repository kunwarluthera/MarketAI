"""Pure, deterministic Layer 2.5 research-priority evaluation.

This module deliberately has no database, trading, ML, LLM, or execution
dependencies. Callers assemble point-in-time inputs from Layers 2.3 and 2.4.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Orientation = Literal[
    "positive_alignment", "negative_alignment", "mixed", "neutral", "caution", "unavailable"
]
State = Literal[
    "high_priority_research",
    "medium_priority_research",
    "low_priority_research",
    "monitor",
    "insufficient_data",
    "suppressed",
    "expired",
]


@dataclass(frozen=True)
class OpportunityInput:
    instrument_id: str
    evaluated_at: datetime
    technical_directions: tuple[str, ...] = ()
    external_directions: tuple[str, ...] = ()
    technical_ready: bool = True
    external_ready: bool = True
    active_instrument: bool = True
    required_inputs_missing: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()
    expires_at: datetime | None = None


@dataclass(frozen=True)
class OpportunityResult:
    instrument_id: str
    evaluated_at: datetime
    expires_at: datetime | None
    orientation: Orientation
    state: State
    score: int
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()
    contributions: tuple[dict[str, object], ...] = field(default_factory=tuple)


def evaluate_opportunity(inputs: OpportunityInput) -> OpportunityResult:
    """Evaluate a research priority using stable, capped rule contributions."""
    blockers = list(inputs.required_inputs_missing)
    if not inputs.active_instrument:
        blockers.append("INACTIVE_INSTRUMENT")
    if not inputs.technical_ready:
        blockers.append("TECHNICAL_DATA_NOT_READY")
    if not inputs.external_ready:
        blockers.append("EXTERNAL_DATA_NOT_READY")
    if inputs.expires_at is not None and inputs.evaluated_at >= inputs.expires_at:
        return OpportunityResult(
            inputs.instrument_id,
            inputs.evaluated_at,
            inputs.expires_at,
            "unavailable",
            "expired",
            0,
            tuple(dict.fromkeys(blockers)),
            inputs.caution_flags,
        )

    contributions: list[dict[str, object]] = []
    score = 0
    tech = set(inputs.technical_directions)
    ext = set(inputs.external_directions)
    for direction in sorted(tech):
        if direction in {"positive", "negative"}:
            amount = 10
            score += amount
            contributions.append(
                {
                    "contribution_code": f"TECH_{direction.upper()}",
                    "contribution_type": "support",
                    "applied_contribution": amount,
                }
            )
    for direction in sorted(ext):
        if direction in {"positive", "negative"}:
            amount = 15
            score += amount
            contributions.append(
                {
                    "contribution_code": f"EXTERNAL_{direction.upper()}",
                    "contribution_type": "support",
                    "applied_contribution": amount,
                }
            )
    if tech & ext and ({"positive"} <= tech & ext or {"negative"} <= tech & ext):
        score += 8
        contributions.append(
            {
                "contribution_code": "CROSS_LAYER_ALIGNMENT",
                "contribution_type": "support",
                "applied_contribution": 8,
            }
        )
    score = min(100, max(0, score))
    if blockers:
        state: State = "insufficient_data"
    elif tech and ext and len(tech | ext) > 1:
        state = "monitor"
    elif score >= 50:
        state = "high_priority_research"
    elif score >= 30:
        state = "medium_priority_research"
    elif score > 0:
        state = "low_priority_research"
    else:
        state = "monitor"
    orientation: Orientation = (
        "mixed"
        if len(tech | ext) > 1
        else (
            "positive_alignment"
            if "positive" in tech | ext
            else "negative_alignment"
            if "negative" in tech | ext
            else "neutral"
        )
    )
    return OpportunityResult(
        inputs.instrument_id,
        inputs.evaluated_at,
        inputs.expires_at,
        orientation,
        state,
        score,
        tuple(dict.fromkeys(blockers)),
        tuple(sorted(set(inputs.caution_flags))),
        tuple(contributions),
    )
