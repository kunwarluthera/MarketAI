"""Pure market calculations; no process-local authoritative state."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


def now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class Tick:
    symbol: str
    price: Decimal
    volume: int
    timestamp: datetime
    source: str = "simulated"


@dataclass(frozen=True)
class Candle:
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    started_at: datetime
    completed_at: datetime


def aggregate_candle(ticks: list[Tick]) -> Candle:
    if not ticks:
        raise ValueError("DATA_MISSING")
    ordered = sorted(ticks, key=lambda t: t.timestamp)
    if len({(t.symbol, t.timestamp) for t in ordered}) != len(ordered):
        raise ValueError("DUPLICATE_TICK")
    prices = [t.price for t in ordered]
    if any(p <= 0 for p in prices):
        raise ValueError("DATA_INVALID")
    return Candle(
        ordered[0].symbol,
        prices[0],
        max(prices),
        min(prices),
        prices[-1],
        sum(t.volume for t in ordered),
        ordered[0].timestamp,
        ordered[-1].timestamp,
    )


def features(candles: list[Candle]) -> dict[str, Any]:
    if len(candles) < 5:
        return {"ready": False, "missing_fields": ["history_5"], "quality": "incomplete"}
    closes = [c.close for c in candles]
    typical = Decimal(sum(c.volume for c in candles[:-1])) / Decimal(max(1, len(candles) - 1))
    vwap = sum(
        (((c.high + c.low + c.close) / Decimal("3")) * c.volume for c in candles),
        Decimal("0"),
    ) / Decimal(sum(c.volume for c in candles))
    ema = closes[0]
    alpha = Decimal("0.333333")
    for close in closes[1:]:
        ema = close * alpha + ema * (1 - alpha)
    gains = [max(Decimal("0"), closes[i] - closes[i - 1]) for i in range(1, len(closes))]
    losses = [max(Decimal("0"), closes[i - 1] - closes[i]) for i in range(1, len(closes))]
    avg_gain, avg_loss = sum(gains) / Decimal(len(gains)), sum(losses) / Decimal(len(losses))
    rsi = (
        Decimal("100")
        if avg_loss == 0
        else Decimal("100") - Decimal("100") / (Decimal("1") + avg_gain / avg_loss)
    )
    return {
        "ready": True,
        "quality": "valid",
        "vwap": vwap,
        "ema": ema,
        "rsi": rsi,
        "relative_volume": Decimal(str(Decimal(candles[-1].volume) / max(Decimal("1"), typical))),
        "price_vs_vwap": closes[-1] - vwap,
        "feature_version": "1.0.0",
    }


def regime(candles: list[Candle]) -> dict[str, Any]:
    if len(candles) < 5:
        return {"regime": "weak_or_invalid_data", "confidence": 0, "version": "1.0.0"}
    change = (candles[-1].close - candles[0].close) / candles[0].close * 100
    ranges = [(c.high - c.low) / c.close * 100 for c in candles]
    value = (
        "high_volatility"
        if sum(ranges) / len(ranges) > Decimal("3")
        else "trending_up"
        if change > Decimal("0.6")
        else "trending_down"
        if change < Decimal("-0.6")
        else "sideways"
    )
    return {"regime": value, "confidence": 82, "version": "1.0.0"}
