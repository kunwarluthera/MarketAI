from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class EvidenceDefinition:
    code: str
    display_name: str
    category: str
    rule_version: str
    required_features: tuple[str, ...]
    expiry_bars: int


REGISTRY = {
    "PRICE_ABOVE_EMA": EvidenceDefinition(
        "PRICE_ABOVE_EMA", "Price relative to EMA", "trend", "1", ("ema",), 1
    ),
    "TREND_SLOPE": EvidenceDefinition(
        "TREND_SLOPE", "Trend slope", "trend", "1", ("trend_slope",), 1
    ),
    "RSI_STATE": EvidenceDefinition("RSI_STATE", "RSI state", "momentum", "1", ("rsi",), 1),
    "RELATIVE_VOLUME": EvidenceDefinition(
        "RELATIVE_VOLUME", "Relative volume", "volume", "1", ("relative_volume",), 1
    ),
    "PROVIDER_FRESHNESS": EvidenceDefinition(
        "PROVIDER_FRESHNESS", "Provider freshness", "data_quality", "1", (), 1
    ),
}


def evaluate(
    code: str, values: dict, evaluation_time: datetime, next_bar: datetime | None = None
) -> dict:
    definition = REGISTRY[code]
    if any(values.get(name) is None for name in definition.required_features):
        return {
            "direction": "unavailable",
            "state": "missing_input",
            "strength": 0.0,
            "expires_at": next_bar or evaluation_time,
        }
    if code == "PRICE_ABOVE_EMA":
        distance = float(values["close"]) - float(values["ema"])
        direction = "bullish" if distance > 0 else "bearish" if distance < 0 else "neutral"
        strength = min(1.0, abs(distance) / max(abs(float(values.get("atr", 1))), 1e-12))
        state = "above" if distance > 0 else "below" if distance < 0 else "near"
    elif code == "TREND_SLOPE":
        slope = float(values["trend_slope"])
        direction, state = (
            ("bullish", "positive")
            if slope > 0
            else ("bearish", "negative")
            if slope < 0
            else ("neutral", "flat")
        )
        strength = min(1.0, abs(slope))
    elif code == "RSI_STATE":
        rsi = float(values["rsi"])
        state = "overbought" if rsi >= 70 else "oversold" if rsi <= 30 else "neutral"
        direction = "caution" if state != "neutral" else "neutral"
        strength = min(1.0, abs(rsi - 50) / 50)
    elif code == "RELATIVE_VOLUME":
        volume = float(values["relative_volume"])
        state = "elevated" if volume >= 1.5 else "low" if volume < 0.75 else "normal"
        direction, strength = "neutral", min(1.0, abs(volume - 1))
    else:
        fresh = values.get("status") == "fresh"
        state, direction, strength = (
            ("fresh", "neutral", 1.0) if fresh else ("stale", "unavailable", 0.0)
        )
    return {
        "direction": direction,
        "state": state,
        "strength": strength,
        "expires_at": next_bar or evaluation_time + timedelta(minutes=1),
    }
