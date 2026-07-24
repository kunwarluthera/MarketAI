from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.models import (
    IntelligenceCandle,
    IntelligenceCandleRejection,
    IntelligenceInstrument,
    uid,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


def session_for_timestamp(session: Session, value: datetime):
    from app.common.models import IntelligenceTradingSession

    return session.scalar(
        select(IntelligenceTradingSession).where(
            IntelligenceTradingSession.market_open <= value,
            IntelligenceTradingSession.market_close >= value,
            IntelligenceTradingSession.is_holiday.is_(False),
        )
    )


def provider_status_at(
    session: Session, provider: str, evaluation_time: datetime, threshold_seconds: int = 300
) -> str:
    from app.common.models import IntelligenceProviderStatus

    row = session.get(IntelligenceProviderStatus, provider)
    if row is None or row.last_received_at is None:
        return "unknown"
    age = int((evaluation_time - row.last_received_at).total_seconds())
    return "fresh" if age <= threshold_seconds else "stale"


def validate_candle(data: dict, received_at: datetime | None = None) -> list[str]:
    now = received_at or utcnow()
    errors: list[str] = []
    if data["ended_at"] <= data["started_at"]:
        errors.append("INVALID_TIME_RANGE")
    if data["source_timestamp"] > now:
        errors.append("FUTURE_SOURCE_TIMESTAMP")
    if data["high"] < data["low"]:
        errors.append("HIGH_BELOW_LOW")
    if data["high"] < max(data["open"], data["close"]):
        errors.append("HIGH_BELOW_OHLC")
    if data["low"] > min(data["open"], data["close"]):
        errors.append("LOW_ABOVE_OHLC")
    if any(Decimal(str(data[key])) <= 0 for key in ("open", "high", "low", "close")):
        errors.append("NON_POSITIVE_PRICE")
    if data["volume"] < 0 or data.get("trade_count", 0) < 0:
        errors.append("NEGATIVE_COUNT")
    if not data.get("is_complete", True) and data["ended_at"] <= now:
        errors.append("INCOMPLETE_CLOSED_CANDLE")
    return errors


def upsert_instrument(
    session: Session, exchange: str, symbol: str, valid_from: datetime, **metadata: object
) -> IntelligenceInstrument:
    row = IntelligenceInstrument(
        id=uid(),
        exchange=exchange,
        symbol=symbol,
        valid_from=valid_from,
        is_active=True,
        metadata_version=1,
        metadata_json=metadata,
        instrument_type=str(metadata.get("instrument_type", "equity")),
        exchange_token=metadata.get("exchange_token"),
        sector=metadata.get("sector"),
        created_at=valid_from,
        updated_at=valid_from,
    )
    session.add(row)
    session.flush()
    return row


def ingest_candle(session: Session, instrument_id: str, data: dict) -> IntelligenceCandle:
    received_at = data.get("received_at") or utcnow()
    errors = validate_candle(data, received_at)
    if errors:
        audit_payload = {
            key: value.isoformat()
            if isinstance(value, datetime)
            else str(value)
            if isinstance(value, Decimal)
            else value
            for key, value in data.items()
        }
        session.add(
            IntelligenceCandleRejection(
                instrument_id=instrument_id,
                interval=data["interval"],
                source=data["source"],
                source_timestamp=data.get("source_timestamp"),
                received_at=received_at,
                raw_payload=audit_payload,
                error_codes=errors,
                created_at=received_at,
            )
        )
        session.flush()
        raise ValueError("CANDLE_REJECTED:" + ",".join(errors))
    existing = session.scalar(
        select(IntelligenceCandle).where(
            IntelligenceCandle.instrument_id == instrument_id,
            IntelligenceCandle.interval == data["interval"],
            IntelligenceCandle.started_at == data["started_at"],
            IntelligenceCandle.source == data["source"],
        )
    )
    if existing is not None:
        same_payload = (
            all(
                getattr(existing, field) == Decimal(str(data[key]))
                for field, key in (
                    ("open_price", "open"),
                    ("high_price", "high"),
                    ("low_price", "low"),
                    ("close_price", "close"),
                )
            )
            and existing.volume == data["volume"]
        )
        if existing.validation_status == "valid" and same_payload:
            return existing
        existing.is_authoritative = False
        revision = (
            session.scalar(
                select(func.max(IntelligenceCandle.revision)).where(
                    IntelligenceCandle.instrument_id == instrument_id,
                    IntelligenceCandle.interval == data["interval"],
                    IntelligenceCandle.started_at == data["started_at"],
                    IntelligenceCandle.source == data["source"],
                )
            )
            or 0
        ) + 1
    else:
        revision = 1
    row = IntelligenceCandle(
        id=uid(),
        instrument_id=instrument_id,
        interval=data["interval"],
        source=data["source"],
        session_id=data.get("session_id"),
        open_price=Decimal(str(data["open"])),
        high_price=Decimal(str(data["high"])),
        low_price=Decimal(str(data["low"])),
        close_price=Decimal(str(data["close"])),
        volume=data["volume"],
        trade_count=data.get("trade_count", 0),
        started_at=data["started_at"],
        ended_at=data["ended_at"],
        source_timestamp=data["source_timestamp"],
        received_at=received_at,
        freshness_seconds=max(0, int((received_at - data["source_timestamp"]).total_seconds())),
        is_complete=data.get("is_complete", True),
        revision=revision,
        is_authoritative=True,
        validation_status="valid",
        validation_errors=[],
        created_at=received_at,
        updated_at=received_at,
    )
    session.add(row)
    session.flush()
    return row
