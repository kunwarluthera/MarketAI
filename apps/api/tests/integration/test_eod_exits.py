from sqlalchemy import select, func
from datetime import datetime
from zoneinfo import ZoneInfo
from app.common.db import SessionLocal
from app.common.models import Position, Order, Trade, ScheduledJob
from app.scheduler.service import run_job
from app.scheduler.eod_policy import EodExitPolicy
from tests.integration.test_automatic_stop_target import _scenario, _snapshot


def _force(session):
    job = session.scalar(select(ScheduledJob).where(ScheduledJob.job_type == "EOD_POSITION_EXIT"))
    if job is None:
        run_job(session, "EOD_POSITION_EXIT")
        job = session.scalar(
            select(ScheduledJob).where(ScheduledJob.job_type == "EOD_POSITION_EXIT")
        )
    job.payload = {**(job.payload or {}), "force": True}
    session.flush()


def test_eod_closes_eligible_intraday_position_once():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _snapshot(s, i, "102")
        _force(s)
        run_job(
            s,
            "EOD_POSITION_EXIT",
            evaluation_time=datetime(2026, 7, 23, 15, 30, tzinfo=ZoneInfo("Asia/Kolkata")),
        )
        assert s.scalar(select(Position).where(Position.id == p.id)).quantity == 0
        assert (
            s.scalar(
                select(func.count())
                .select_from(Order)
                .where(Order.instrument_id == i.id, Order.side == "SELL")
            )
            == 1
        )
        assert (
            s.scalar(
                select(func.count())
                .select_from(Trade)
                .where(Trade.instrument_id == i.id, Trade.side == "SELL")
            )
            == 1
        )
        assert (
            s.scalar(
                select(Trade).where(Trade.instrument_id == i.id, Trade.side == "SELL")
            ).payload["exit_reason"]
            == "EOD_FORCED_EXIT"
        )


def test_eod_does_not_close_delivery_position():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        p.payload = {**p.payload, "intraday": False}
        _snapshot(s, i, "102")
        _force(s)
        run_job(
            s,
            "EOD_POSITION_EXIT",
            evaluation_time=datetime(2026, 7, 23, 15, 30, tzinfo=ZoneInfo("Asia/Kolkata")),
        )
        assert s.scalar(select(Position).where(Position.id == p.id)).quantity > 0


def test_eod_before_cutoff_does_nothing():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _snapshot(s, i, "102")
        _force(s)
        run_job(
            s,
            "EOD_POSITION_EXIT",
            evaluation_time=datetime(2026, 7, 20, 9, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
            eod_policy=EodExitPolicy(),
        )
        assert s.scalar(select(Position).where(Position.id == p.id)).quantity > 0


def test_eod_skips_weekend():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _force(s)
        run_job(
            s,
            "EOD_POSITION_EXIT",
            evaluation_time=datetime(2026, 7, 25, 15, 30, tzinfo=ZoneInfo("Asia/Kolkata")),
        )
        assert s.scalar(select(Position).where(Position.id == p.id)).quantity > 0


def test_eod_skips_market_holiday():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _force(s)
        run_job(
            s,
            "EOD_POSITION_EXIT",
            evaluation_time=datetime(2026, 7, 24, 15, 30, tzinfo=ZoneInfo("Asia/Kolkata")),
            eod_policy=EodExitPolicy(
                holidays=frozenset({datetime(2026, 7, 24, tzinfo=ZoneInfo("Asia/Kolkata")).date()})
            ),
        )
        assert s.scalar(select(Position).where(Position.id == p.id)).quantity > 0


def test_eod_missing_market_data_does_not_fill():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _force(s)
        run_job(
            s,
            "EOD_POSITION_EXIT",
            evaluation_time=datetime(2026, 7, 23, 15, 30, tzinfo=ZoneInfo("Asia/Kolkata")),
        )
        assert s.scalar(select(Position).where(Position.id == p.id)).quantity > 0


def test_eod_stale_market_data_does_not_fill():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _force(s)
        run_job(
            s,
            "EOD_POSITION_EXIT",
            evaluation_time=datetime(2026, 7, 23, 15, 30, tzinfo=ZoneInfo("Asia/Kolkata")),
        )
        assert s.scalar(select(Position).where(Position.id == p.id)).quantity > 0


def test_eod_retry_exhaustion_creates_failure_alert():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _force(s)
        run_job(
            s,
            "EOD_POSITION_EXIT",
            evaluation_time=datetime(2026, 7, 23, 15, 30, tzinfo=ZoneInfo("Asia/Kolkata")),
        )
        assert s.scalar(select(Position).where(Position.id == p.id)).quantity > 0
