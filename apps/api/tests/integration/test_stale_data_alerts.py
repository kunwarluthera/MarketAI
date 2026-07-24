from datetime import timedelta
from decimal import Decimal
from sqlalchemy import select, func

from app.common.db import SessionLocal
from app.common.models import Alert, Instrument, MarketSnapshot, uid
from app.paper_trading.service import utcnow, seed
from app.scheduler.service import run_job


def _instrument(session):
    seed(session)
    t = utcnow()
    row = Instrument(
        id=uid(),
        symbol=f"STALE_{uid()[:8]}",
        exchange="NSE",
        sector="TEST",
        eligible=True,
        created_at=t,
        updated_at=t,
    )
    session.add(row)
    session.flush()
    return row


def test_missing_data_creates_open_alert():
    with SessionLocal.begin() as s:
        i = _instrument(s)
        run_job(s, "STALE_DATA_CHECK")
        alert = s.scalar(
            select(Alert).where(
                Alert.instrument_id == i.id, Alert.alert_type == "MARKET_DATA_MISSING"
            )
        )
        assert alert and alert.status == "open"


def test_repeated_missing_check_updates_existing_alert():
    with SessionLocal.begin() as s:
        i = _instrument(s)
        run_job(s, "STALE_DATA_CHECK")
        run_job(s, "STALE_DATA_CHECK")
        assert (
            s.scalar(
                select(func.count())
                .select_from(Alert)
                .where(
                    Alert.instrument_id == i.id,
                    Alert.issue_key == f"MARKET_DATA_MISSING:{i.id}",
                    Alert.status == "open",
                )
            )
            == 1
        )


def test_fresh_data_resolves_missing_alert():
    with SessionLocal.begin() as s:
        i = _instrument(s)
        run_job(s, "STALE_DATA_CHECK")
        t = utcnow()
        s.add(
            MarketSnapshot(
                instrument_id=i.id,
                price=Decimal("100"),
                volume=1,
                exchange_timestamp=t,
                ingested_at=t,
                occurrence_key=f"fresh-{i.id}",
                created_at=t,
                updated_at=t,
            )
        )
        run_job(s, "STALE_DATA_CHECK")
        alert = s.scalar(
            select(Alert).where(
                Alert.instrument_id == i.id, Alert.issue_key == f"MARKET_DATA_MISSING:{i.id}"
            )
        )
        assert alert.status == "resolved" and alert.resolved_at


def test_stale_data_creates_open_alert():
    with SessionLocal.begin() as s:
        i = _instrument(s)
        t = utcnow() - timedelta(minutes=10)
        s.add(
            MarketSnapshot(
                instrument_id=i.id,
                price=Decimal("100"),
                volume=1,
                exchange_timestamp=t,
                ingested_at=t,
                occurrence_key=f"stale-{i.id}",
                created_at=t,
                updated_at=t,
            )
        )
        run_job(s, "STALE_DATA_CHECK")
        alert = s.scalar(
            select(Alert).where(
                Alert.instrument_id == i.id, Alert.alert_type == "MARKET_DATA_STALE"
            )
        )
        assert alert and alert.status == "open" and alert.payload["max_age_seconds"] == 300


def test_repeated_stale_check_updates_existing_alert():
    with SessionLocal.begin() as s:
        i = _instrument(s)
        t = utcnow() - timedelta(minutes=10)
        s.add(
            MarketSnapshot(
                instrument_id=i.id,
                price=Decimal("100"),
                volume=1,
                exchange_timestamp=t,
                ingested_at=t,
                occurrence_key=f"stale2-{i.id}",
                created_at=t,
                updated_at=t,
            )
        )
        run_job(s, "STALE_DATA_CHECK")
        run_job(s, "STALE_DATA_CHECK")
        assert (
            s.scalar(
                select(func.count())
                .select_from(Alert)
                .where(
                    Alert.instrument_id == i.id,
                    Alert.alert_type == "MARKET_DATA_STALE",
                    Alert.status == "open",
                )
            )
            == 1
        )


def test_fresh_data_resolves_stale_alert():
    with SessionLocal.begin() as s:
        i = _instrument(s)
        old = utcnow() - timedelta(minutes=10)
        s.add(
            MarketSnapshot(
                instrument_id=i.id,
                price=Decimal("100"),
                volume=1,
                exchange_timestamp=old,
                ingested_at=old,
                occurrence_key=f"stale3-{i.id}",
                created_at=old,
                updated_at=old,
            )
        )
        run_job(s, "STALE_DATA_CHECK")
        t = utcnow()
        s.add(
            MarketSnapshot(
                instrument_id=i.id,
                price=Decimal("100"),
                volume=1,
                exchange_timestamp=t,
                ingested_at=t,
                occurrence_key=f"fresh3-{i.id}",
                created_at=t,
                updated_at=t,
            )
        )
        run_job(s, "STALE_DATA_CHECK")
        alert = s.scalar(
            select(Alert).where(
                Alert.instrument_id == i.id, Alert.alert_type == "MARKET_DATA_STALE"
            )
        )
        assert alert.status == "resolved"


def test_missing_and_stale_alerts_are_scoped_per_instrument():
    with SessionLocal.begin() as s:
        first, second = _instrument(s), _instrument(s)
        run_job(s, "STALE_DATA_CHECK")
        assert s.scalar(select(Alert).where(Alert.instrument_id == first.id)) and s.scalar(
            select(Alert).where(Alert.instrument_id == second.id)
        )
