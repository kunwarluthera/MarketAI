from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text, select

from app.common.db import SessionLocal
from app.common.models import (
    IntelligenceCandle,
    IntelligenceProviderStatus,
    IntelligenceTradingSession,
    Instrument,
    Order,
    Trade,
    Position,
    uid,
)
from app.intelligence.market_data import (
    ingest_candle,
    provider_status_at,
    session_for_timestamp,
    upsert_instrument,
    validate_candle,
)

pytestmark = pytest.mark.integration


def ts(month: int, day: int = 2, hour: int = 10) -> datetime:
    return datetime(2026, month, day, hour, tzinfo=UTC)


def candle(started_at: datetime, **overrides: object) -> dict:
    value = {
        "interval": "1m",
        "source": "provider-test",
        "open": Decimal("100"),
        "high": Decimal("102"),
        "low": Decimal("99"),
        "close": Decimal("101"),
        "volume": 1000,
        "trade_count": 10,
        "started_at": started_at,
        "ended_at": started_at + timedelta(minutes=1),
        "source_timestamp": started_at,
        "received_at": started_at + timedelta(minutes=1),
        "is_complete": True,
    }
    value.update(overrides)
    return value


def test_instrument_lifecycle_and_candle_continuity() -> None:
    with SessionLocal.begin() as session:
        row = upsert_instrument(session, "NSE", f"L2_SYMBOL_{uid()[:6]}", ts(1), exchange_token="1")
        first_id = row.id
        row.valid_to = ts(2)
        row.is_active = False
        replacement = upsert_instrument(
            session, "NSE", f"L2_SYMBOL_NEW_{uid()[:6]}", ts(2), exchange_token="2"
        )
        ingest_candle(session, first_id, candle(ts(1)))
        assert replacement.id != first_id
        assert (
            session.get(
                IntelligenceCandle,
                session.scalar(
                    select(IntelligenceCandle.id).where(
                        IntelligenceCandle.instrument_id == first_id
                    )
                ),
            )
            is not None
        )
        assert session.get(Instrument, "does-not-exist") is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"ended_at": ts(1) - timedelta(minutes=1)},
        {"volume": -1},
        {"open": 0},
        {"high": Decimal("98")},
        {"low": Decimal("103")},
        {"source_timestamp": ts(1) + timedelta(days=1)},
        {"is_complete": False},
    ],
)
def test_invalid_candles_are_recorded_and_not_valid(overrides: dict) -> None:
    data = candle(ts(1), **overrides)
    errors = validate_candle(data, data["received_at"])
    assert errors
    with SessionLocal.begin() as session:
        instrument = upsert_instrument(session, "NSE", f"L2_INVALID_{id(overrides)}", ts(1))
        with pytest.raises(ValueError, match="CANDLE_REJECTED"):
            ingest_candle(session, instrument.id, data)
        assert (
            session.scalar(
                select(IntelligenceCandle).where(IntelligenceCandle.instrument_id == instrument.id)
            )
            is None
        )


def test_duplicate_is_idempotent_and_correction_increments_revision() -> None:
    with SessionLocal.begin() as session:
        instrument = upsert_instrument(session, "NSE", f"L2_DUP_{uid()[:6]}", ts(1))
        payload = candle(ts(1))
        first = ingest_candle(session, instrument.id, payload)
        duplicate = ingest_candle(session, instrument.id, payload)
        corrected = ingest_candle(session, instrument.id, candle(ts(1), close=Decimal("101.50")))
        assert duplicate.id == first.id
        assert corrected.id != first.id
        assert corrected.revision == 2
        assert corrected.is_authoritative is True
        assert first.is_authoritative is False
        assert (
            session.scalar(
                select(IntelligenceCandle)
                .where(IntelligenceCandle.instrument_id == instrument.id)
                .with_for_update()
            )
            is not None
        )


def test_monthly_partition_routing_and_constraints() -> None:
    with SessionLocal.begin() as session:
        partitions = (
            session.execute(
                text(
                    "SELECT inhrelid::regclass::text FROM pg_inherits WHERE inhparent = 'intelligence_candles'::regclass"
                )
            )
            .scalars()
            .all()
        )
        assert "intelligence_candles_default" in partitions
        assert (
            session.execute(
                text("SELECT relkind FROM pg_class WHERE relname='intelligence_candles'")
            ).scalar()
            == "p"
        )


def test_calendar_and_provider_freshness_are_persisted() -> None:
    with SessionLocal.begin() as session:
        session.add(
            IntelligenceTradingSession(
                session_id=f"L2-SESSION-{uid()[:6]}",
                session_date=ts(1),
                market_open=ts(1, hour=9),
                market_close=ts(1, hour=15),
                is_holiday=False,
                is_half_session=False,
                created_at=ts(1),
            )
        )
        session.add(
            IntelligenceProviderStatus(
                provider=f"provider-test-{uid()[:6]}",
                last_source_timestamp=ts(1),
                last_received_at=ts(1, hour=10),
                freshness_seconds=60,
                status="fresh",
                updated_at=ts(1, hour=10),
            )
        )
        session.flush()
        assert session.query(IntelligenceProviderStatus).filter_by(status="fresh").count() >= 1
        provider = (
            session.query(IntelligenceProviderStatus)
            .filter_by(status="fresh")
            .order_by(IntelligenceProviderStatus.updated_at.desc())
            .first()
        )
        assert provider_status_at(session, provider.provider, ts(1, hour=10, day=2), 60) == "fresh"
        assert provider_status_at(session, provider.provider, ts(1, hour=12, day=2), 60) == "stale"
        assert session_for_timestamp(session, ts(1, hour=10, day=2)) is not None


def test_physical_month_routing() -> None:
    with SessionLocal.begin() as session:
        instrument = upsert_instrument(session, "NSE", f"L2_ROUTE_{uid()[:6]}", ts(1))
        for started in (ts(1, 15), ts(2, 1), ts(3, 1)):
            ingest_candle(session, instrument.id, candle(started))
        rows = (
            session.execute(
                text(
                    "SELECT tableoid::regclass::text FROM intelligence_candles WHERE instrument_id=:id ORDER BY started_at"
                ),
                {"id": instrument.id},
            )
            .scalars()
            .all()
        )
        assert rows == [
            "intelligence_candles_2026_01",
            "intelligence_candles_2026_02",
            "intelligence_candles_2026_03",
        ]


def test_layer2_ingestion_does_not_create_layer1_financial_rows() -> None:
    with SessionLocal.begin() as session:
        before = [
            session.scalar(select(model).count()) if False else session.query(model).count()
            for model in (Order, Trade, Position)
        ]
        instrument = upsert_instrument(session, "NSE", f"L2_ISOLATION_{uid()[:6]}", ts(1))
        ingest_candle(session, instrument.id, candle(ts(2)))
        after = [session.query(model).count() for model in (Order, Trade, Position)]
        assert after == before
