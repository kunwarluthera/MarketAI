from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.models import FeatureValue, IntelligenceCandle, uid
from .engine import (
    REGISTRY,
    atr,
    bar_vwap,
    ema,
    period_return,
    relative_volume,
    rsi,
    sma,
    trend_slope,
)


def calculate_feature(
    session: Session,
    instrument_id: str,
    interval: str,
    feature_name: str,
    evaluation_time: datetime,
) -> FeatureValue:
    definition = REGISTRY[feature_name]
    candles = session.scalars(
        select(IntelligenceCandle)
        .where(
            IntelligenceCandle.instrument_id == instrument_id,
            IntelligenceCandle.interval == interval,
            IntelligenceCandle.started_at <= evaluation_time,
            IntelligenceCandle.is_authoritative.is_(True),
        )
        .order_by(IntelligenceCandle.started_at)
    ).all()
    values = {
        "sma": sma,
        "ema": ema,
        "rsi": rsi,
        "atr": atr,
        "bar_vwap": bar_vwap,
        "return": period_return,
        "relative_volume": relative_volume,
        "trend_slope": trend_slope,
    }
    value = (
        values[feature_name](candles, definition.lookback)
        if feature_name not in {"bar_vwap"}
        else values[feature_name](candles)
    )
    observed_at = candles[-1].started_at if candles else evaluation_time
    existing = session.scalar(
        select(FeatureValue).where(
            FeatureValue.instrument_id == instrument_id,
            FeatureValue.interval == interval,
            FeatureValue.observed_at == observed_at,
            FeatureValue.feature_name == feature_name,
            FeatureValue.feature_version == definition.version,
        )
    )
    if existing is not None:
        existing.value = None if value is None else Decimal(str(value))
        existing.calculated_at = datetime.now(UTC)
        return existing
    row = FeatureValue(
        id=uid(),
        instrument_id=instrument_id,
        interval=interval,
        observed_at=observed_at,
        feature_name=feature_name,
        feature_version=definition.version,
        value=None if value is None else Decimal(str(value)),
        calculation_version="1",
        source_started_at=candles[0].started_at if candles else None,
        source_ended_at=candles[-1].ended_at if candles else None,
        calculated_at=datetime.now(UTC),
        lineage={"candle_ids": [c.id for c in candles], "cutoff": evaluation_time.isoformat()},
    )
    session.add(row)
    session.flush()
    return row
