from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class FeatureDefinition:
    name: str
    version: str
    description: str
    lookback: int
    unit: str


REGISTRY = {
    "sma": FeatureDefinition("sma", "1", "Simple moving average", 1, "price"),
    "ema": FeatureDefinition("ema", "1", "Exponential moving average", 1, "price"),
    "rsi": FeatureDefinition("rsi", "1", "Wilder relative strength index", 14, "ratio"),
    "atr": FeatureDefinition("atr", "1", "Average true range", 14, "price"),
    "bar_vwap": FeatureDefinition("bar_vwap", "1", "Volume weighted average from bars", 1, "price"),
    "return": FeatureDefinition("return", "1", "Period return", 1, "ratio"),
    "relative_volume": FeatureDefinition(
        "relative_volume", "1", "Volume divided by rolling mean", 20, "ratio"
    ),
    "trend_slope": FeatureDefinition("trend_slope", "1", "Least-squares close slope", 20, "price"),
}


def _closes(candles):
    return [float(c["close"]) for c in candles]


def sma(candles, window: int) -> float | None:
    values = _closes(candles)[-window:]
    return mean(values) if len(values) == window else None


def ema(candles, window: int) -> float | None:
    values = _closes(candles)
    if len(values) < window:
        return None
    result = mean(values[:window])
    alpha = 2 / (window + 1)
    for value in values[window:]:
        result = alpha * value + (1 - alpha) * result
    return result


def rsi(candles, window: int = 14) -> float | None:
    values = _closes(candles)
    if len(values) <= window:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))][-window:]
    gains = mean(max(x, 0) for x in changes)
    losses = mean(max(-x, 0) for x in changes)
    return 100.0 if losses == 0 else 100 - (100 / (1 + gains / losses))


def true_range(candles):
    out = []
    for i, candle in enumerate(candles):
        previous = float(candles[i - 1]["close"]) if i else float(candle["close"])
        out.append(
            max(
                float(candle["high"]) - float(candle["low"]),
                abs(float(candle["high"]) - previous),
                abs(float(candle["low"]) - previous),
            )
        )
    return out


def atr(candles, window: int = 14) -> float | None:
    values = true_range(candles)
    return mean(values[-window:]) if len(values) >= window else None


def bar_vwap(candles) -> float | None:
    if not candles:
        return None
    volume = sum(float(c["volume"]) for c in candles)
    return (
        sum(
            ((float(c["high"]) + float(c["low"]) + float(c["close"])) / 3) * float(c["volume"])
            for c in candles
        )
        / volume
        if volume
        else None
    )


def period_return(candles, periods: int = 1) -> float | None:
    values = _closes(candles)
    return values[-1] / values[-1 - periods] - 1 if len(values) > periods else None


def relative_volume(candles, window: int = 20) -> float | None:
    volumes = [float(c["volume"]) for c in candles]
    return (
        volumes[-1] / mean(volumes[-window:])
        if len(volumes) >= window and mean(volumes[-window:])
        else None
    )


def trend_slope(candles, window: int = 20) -> float | None:
    values = _closes(candles)[-window:]
    if len(values) < window:
        return None
    xbar = (window - 1) / 2
    return sum((i - xbar) * (v - mean(values)) for i, v in enumerate(values)) / sum(
        (i - xbar) ** 2 for i in range(window)
    )
