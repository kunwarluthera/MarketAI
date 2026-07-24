"""Focused PostgreSQL verification for the durable stop/target lifecycle."""

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, func, delete

from app.common.db import SessionLocal
from app.common.models import (
    MarketCandle,
    MarketSnapshot,
    Position,
    Trade,
    Order,
    CashLedger,
    AuditLog,
    Instrument,
    ApprovalRequest,
)
from app.paper_trading.service import approve_and_fill, generate_decision, seed, utcnow
from app.common.models import uid
from app.scheduler.service import run_job


pytestmark = pytest.mark.integration


def _scenario(session):
    seed(session)
    base = utcnow() - timedelta(minutes=10)
    instrument = Instrument(
        id=uid(),
        symbol=f"TST_{uid()[:8]}",
        eligible=True,
        exchange="NSE",
        sector="TEST",
        created_at=base,
        updated_at=base,
    )
    session.add(instrument)
    session.flush()
    for n in range(5):
        t = base + timedelta(minutes=n)
        session.add(
            MarketCandle(
                instrument_id=instrument.id,
                interval="1m",
                open=Decimal("100"),
                high=Decimal("102"),
                low=Decimal("99"),
                close=Decimal("101"),
                volume=1000,
                started_at=t,
                completed_at=t + timedelta(seconds=59),
                created_at=t,
                updated_at=t,
            )
        )
    session.flush()
    decision = generate_decision(session, instrument.symbol, "automatic-exit-test")
    if decision.action != "BUY":
        decision.action = "BUY"
        approval = ApprovalRequest(
            decision_id=decision.id,
            status="pending",
            expires_at=utcnow() + timedelta(hours=1),
            version=1,
            payload={},
            created_at=base,
            updated_at=base,
        )
        session.add(approval)
        session.flush()
        decision.payload = {
            **decision.payload,
            "approval_id": approval.id,
            "entry_zone": "100",
            "stop_loss": "95",
            "target": "110",
            "position_size": "10",
        }
    assert instrument is not None and decision is not None
    session.execute(delete(MarketSnapshot).where(MarketSnapshot.instrument_id == instrument.id))
    decision.payload = {**decision.payload, "position_size": "10"}
    session.flush()
    approval_id = decision.payload["approval_id"]
    entry = approve_and_fill(
        session, approval_id, f"automatic-exit-{instrument.id}", "automatic-exit-test"
    )
    position = session.scalar(
        select(Position).where(Position.instrument_id == instrument.id, Position.quantity > 0)
    )
    assert position is not None and entry.filled_quantity == Decimal("10")
    position.average_price = Decimal("100")
    position.current_price = Decimal("100")
    position.payload = {**position.payload, "stop_loss": "95", "target": "110", "intraday": True}
    session.flush()
    return instrument, position


def _snapshot(session, instrument, price):
    now = utcnow()
    session.add(
        MarketSnapshot(
            instrument_id=instrument.id,
            price=Decimal(price),
            volume=100,
            exchange_timestamp=now,
            ingested_at=now,
            occurrence_key=f"test-{now.timestamp()}",
            created_at=now,
            updated_at=now,
        )
    )


def _candle(session, instrument, low, high, completed=True, future=False):
    now = utcnow() + (timedelta(minutes=5) if future else -timedelta(minutes=2))
    session.add(
        MarketCandle(
            instrument_id=instrument.id,
            interval="1m",
            open=Decimal("100"),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal("100"),
            volume=100,
            started_at=now,
            completed_at=now + (timedelta(seconds=59) if completed else timedelta(minutes=5)),
            created_at=now,
            updated_at=now,
        )
    )


def _run(session):
    return run_job(session, "STOP_TARGET_EVALUATION")


def test_quote_stop_closes_position_once():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        s.execute(delete(MarketCandle).where(MarketCandle.instrument_id == i.id))
        _snapshot(s, i, "94")
        _run(s)
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
                .select_from(Order)
                .where(Order.instrument_id == i.id, Order.side == "SELL")
            )
            == 1
        )
        assert (
            s.scalar(
                select(Trade).where(Trade.instrument_id == i.id, Trade.side == "SELL")
            ).payload["exit_reason"]
            == "STOP_LOSS_TRIGGERED"
        )
        counts = [
            s.scalar(select(func.count()).select_from(t))
            for t in (Order, Trade, CashLedger, AuditLog)
        ]
        _run(s)
        assert counts == [
            s.scalar(select(func.count()).select_from(t))
            for t in (Order, Trade, CashLedger, AuditLog)
        ]


def test_completed_candle_stop_closes_position_once():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _candle(s, i, "94", "101")
        _snapshot(s, i, "97")
        _run(s)
        trade = s.scalar(select(Trade).where(Trade.instrument_id == i.id, Trade.side == "SELL"))
        assert trade.payload["exit_reason"] == "STOP_LOSS_TRIGGERED"


def test_quote_target_closes_position_once():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        s.execute(delete(MarketCandle).where(MarketCandle.instrument_id == i.id))
        _snapshot(s, i, "111")
        _run(s)
        trade = s.scalar(select(Trade).where(Trade.instrument_id == i.id, Trade.side == "SELL"))
        assert trade.payload["exit_reason"] == "TARGET_TRIGGERED" and trade.realised_pnl > 0


def test_completed_candle_target_closes_position_once():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _candle(s, i, "99", "111")
        _snapshot(s, i, "108")
        _run(s)
        assert (
            s.scalar(
                select(Trade).where(Trade.instrument_id == i.id, Trade.side == "SELL")
            ).payload["exit_reason"]
            == "TARGET_TRIGGERED"
        )


def test_same_candle_uses_conservative_stop_first():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _candle(s, i, "94", "112")
        _snapshot(s, i, "106")
        _run(s)
        trade = s.scalar(select(Trade).where(Trade.instrument_id == i.id, Trade.side == "SELL"))
        assert trade.payload["exit_reason"] == "AMBIGUOUS_SAME_CANDLE_STOP_TARGET_CONSERVATIVE_STOP"


def test_incomplete_candle_is_ignored():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _candle(s, i, "94", "112", completed=False)
        _snapshot(s, i, "100")
        _run(s)
        assert s.scalar(select(Position).where(Position.id == p.id)).quantity > 0


def test_future_candle_is_ignored():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _candle(s, i, "94", "112", future=True)
        _snapshot(s, i, "100")
        _run(s)
        assert s.scalar(select(Position).where(Position.id == p.id)).quantity > 0
