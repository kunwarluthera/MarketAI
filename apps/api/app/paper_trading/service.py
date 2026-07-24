from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from random import Random
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import append
from app.common.models import (
    ApprovalRequest,
    CashLedger,
    DecisionEvidence,
    FeatureSnapshot,
    IdempotencyRecord,
    Instrument,
    MarketCandle,
    MarketRegime,
    Order,
    OrderEvent,
    PortfolioSnapshot,
    Position,
    RiskEvaluation,
    RiskRuleResult,
    StrategyRegistry,
    StrategySignal,
    StrategyVersion,
    SystemSetting,
    Trade,
    TradeCandidate,
    TradeDecision,
    TradeReview,
)
from app.domain import Candle, features, regime
from app.portfolio.domain import realised_pnl, weighted_average
from app.risk.domain import evaluate


def utcnow() -> datetime:
    return datetime.now(UTC)


def cash_balance(session: Session) -> Decimal:
    return Decimal(session.scalar(select(func.coalesce(func.sum(CashLedger.amount), 0))) or 0)


def setting(session: Session, key: str, default: dict) -> dict:
    row = session.get(SystemSetting, key)
    return row.value if row else default


def add_ledger(
    session: Session,
    entry_type: str,
    amount: Decimal,
    source_type: str,
    source_id: str,
    event_id: str,
    correlation: str,
) -> CashLedger:
    timestamp = utcnow()
    row = CashLedger(
        entry_type=entry_type,
        amount=amount,
        source_type=source_type,
        source_id=source_id,
        event_id=event_id,
        payload={},
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(row)
    session.flush()
    append(
        session,
        "ledger_entry",
        "cash_ledger",
        row.id,
        {"entry_type": entry_type, "amount": str(amount), "source_id": source_id},
        correlation,
    )
    return row


def snapshot(session: Session, correlation: str) -> PortfolioSnapshot:
    cash = cash_balance(session)
    positions = session.scalars(select(Position).where(Position.quantity > 0)).all()
    value = sum((p.quantity * p.current_price for p in positions), Decimal(0))
    timestamp = utcnow()
    row = PortfolioSnapshot(
        cash=cash,
        market_value=value,
        portfolio_value=cash + value,
        payload={},
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(row)
    session.flush()
    append(
        session,
        "portfolio_snapshot",
        "portfolio",
        row.id,
        {"cash": str(cash), "market_value": str(value)},
        correlation,
    )
    return row


def seed(session: Session) -> dict:
    timestamp = utcnow()
    if session.scalar(select(func.count()).select_from(Instrument)):
        return {"status": "existing", "seed": 42}
    sectors = {
        "RELIANCE": "ENERGY",
        "HDFCBANK": "FINANCIALS",
        "ICICIBANK": "FINANCIALS",
        "INFY": "IT",
        "TCS": "IT",
        "SBIN": "FINANCIALS",
        "LT": "INDUSTRIALS",
        "ITC": "FMCG",
        "BHARTIARTL": "TELECOM",
        "AXISBANK": "FINANCIALS",
        "NIFTY50": "INDEX",
        "BANKNIFTY": "INDEX",
    }
    bases = {
        "RELIANCE": "2950",
        "HDFCBANK": "1680",
        "ICICIBANK": "1220",
        "INFY": "1830",
        "TCS": "4140",
        "SBIN": "820",
        "LT": "3610",
        "ITC": "470",
        "BHARTIARTL": "1510",
        "AXISBANK": "1250",
        "NIFTY50": "24500",
        "BANKNIFTY": "52000",
    }
    rng, base_time = Random(42), timestamp - timedelta(minutes=5)
    instruments: dict[str, Instrument] = {}
    for symbol, base_text in bases.items():
        instrument = Instrument(
            symbol=symbol,
            exchange="NSE",
            sector=sectors[symbol],
            eligible=True,
            created_at=timestamp,
            updated_at=timestamp,
        )
        session.add(instrument)
        session.flush()
        instruments[symbol] = instrument
        price, base = Decimal(base_text), Decimal(base_text)
        for i in range(5):
            opened = price
            price += Decimal(str(rng.uniform(0.001, 0.004))) * base
            session.add(
                MarketCandle(
                    instrument_id=instrument.id,
                    interval="1m",
                    open=opened,
                    high=max(opened, price) + 1,
                    low=min(opened, price) - 1,
                    close=price,
                    volume=10000 + i * 4000,
                    started_at=base_time + timedelta(minutes=i),
                    completed_at=base_time + timedelta(minutes=i, seconds=59),
                    source="simulated",
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
    registry = StrategyRegistry(
        name="VWAP Momentum", payload={"enabled": True}, created_at=timestamp, updated_at=timestamp
    )
    session.add(registry)
    session.flush()
    session.add(
        StrategyVersion(
            strategy_id=registry.id,
            version="1.0.0",
            payload={"eligible_regimes": ["trending_up"]},
            created_at=timestamp,
            updated_at=timestamp,
        )
    )
    session.add(
        SystemSetting(
            key="kill_switch",
            value={"enabled": False},
            version=1,
            created_at=timestamp,
            updated_at=timestamp,
        )
    )
    session.add(
        SystemSetting(
            key="risk_config",
            value={"allow_position_averaging": False, "min_risk_reward": "1.5"},
            version=1,
            created_at=timestamp,
            updated_at=timestamp,
        )
    )
    add_ledger(
        session,
        "INITIAL_CAPITAL",
        Decimal("1000000"),
        "system",
        "seed",
        "initial-capital-v1",
        "seed-42",
    )
    append(
        session, "demo_seeded", "system", "seed", {"seed": 42, "symbols": list(bases)}, "seed-42"
    )
    session.flush()
    snapshot(session, "seed-42")
    return {"status": "seeded", "seed": 42}


def candles_for(session: Session, instrument: Instrument) -> list[Candle]:
    rows = session.scalars(
        select(MarketCandle)
        .where(MarketCandle.instrument_id == instrument.id)
        .order_by(MarketCandle.started_at)
    ).all()
    return [
        Candle(
            instrument.symbol,
            r.open,
            r.high,
            r.low,
            r.close,
            r.volume,
            r.started_at,
            r.completed_at,
        )
        for r in rows
    ]


def scan(session: Session) -> list[dict]:
    result = []
    for instrument in session.scalars(select(Instrument).order_by(Instrument.symbol)).all():
        candles = candles_for(session, instrument)
        if len(candles) < 2:
            continue
        f = features(candles)
        r = regime(candles)
        action = "BUY" if r["regime"] == "trending_up" and f.get("price_vs_vwap", 0) > 0 else "HOLD"
        result.append(
            {
                "symbol": instrument.symbol,
                "price": str(candles[-1].close),
                "change": str((candles[-1].close / candles[-2].close - 1) * 100),
                "relative_volume": str(f.get("relative_volume", "")),
                "regime": r["regime"],
                "technical_score": 78 if action == "BUY" else 50,
                "data_quality": f["quality"],
                "decision": action,
                "confidence": 76 if action == "BUY" else 45,
                "strategy": "VWAP Momentum 1.0.0",
                "risk_reward": "2" if action == "BUY" else None,
            }
        )
    return result


def generate_decision(session: Session, symbol: str, correlation: str) -> TradeDecision:
    timestamp = utcnow()
    instrument = session.scalar(select(Instrument).where(Instrument.symbol == symbol))
    if not instrument:
        raise ValueError("INSTRUMENT_NOT_ELIGIBLE")
    cs = candles_for(session, instrument)
    f = features(cs)
    r = regime(cs)
    last = cs[-1].close
    entry, stop, target = last, last * Decimal("0.99"), last * Decimal("1.02")
    existing = (
        session.scalar(
            select(Position).where(Position.instrument_id == instrument.id, Position.quantity > 0)
        )
        is not None
    )
    kill = setting(session, "kill_switch", {"enabled": True})["enabled"]
    qty, rules = evaluate(entry, stop, target, cash_balance(session), kill, existing)
    eligible = f["ready"] and r["regime"] == "trending_up" and f["price_vs_vwap"] > 0
    passed = all(rule.passed for rule in rules)
    action = "BUY" if eligible and passed else ("REJECT" if kill else "HOLD")
    codes = [rule.reason_code for rule in rules if not rule.passed] or (
        ["APPROVAL_REQUIRED"] if action == "BUY" else ["REGIME_NOT_ELIGIBLE"]
    )
    version = session.scalar(select(StrategyVersion).where(StrategyVersion.version == "1.0.0"))
    if version is None:
        raise ValueError("STRATEGY_VERSION_NOT_FOUND")
    signal = StrategySignal(
        strategy_version_id=version.id,
        instrument_id=instrument.id,
        payload={"signal": action},
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(signal)
    session.flush()
    candidate = TradeCandidate(
        instrument_id=instrument.id,
        strategy_version_id=version.id,
        valid_until=timestamp + timedelta(minutes=5),
        payload={"entry": str(entry), "stop": str(stop), "target": str(target)},
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(candidate)
    session.flush()
    decision = TradeDecision(
        instrument_id=instrument.id,
        candidate_id=candidate.id,
        action=action,
        valid_until=candidate.valid_until,
        payload={
            "symbol": symbol,
            "confidence": 76 if action == "BUY" else 45,
            "entry_zone": str(entry),
            "stop_loss": str(stop),
            "target": str(target),
            "risk_reward": str((target - entry) / (entry - stop)),
            "position_size": qty if action == "BUY" else 0,
            "monetary_risk": str((entry - stop) * qty if action == "BUY" else 0),
            "regime": r,
            "features": {k: str(v) if isinstance(v, Decimal) else v for k, v in f.items()},
            "reason_codes": codes,
            "strategy_version": "vwap-momentum@1.0.0",
        },
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(decision)
    session.flush()
    session.add_all(
        [
            FeatureSnapshot(
                instrument_id=instrument.id,
                valid_until=decision.valid_until,
                version="1.0.0",
                payload=decision.payload["features"],
                created_at=timestamp,
                updated_at=timestamp,
            ),
            MarketRegime(
                instrument_id=instrument.id,
                regime=r["regime"],
                valid_until=decision.valid_until,
                payload=r,
                created_at=timestamp,
                updated_at=timestamp,
            ),
            DecisionEvidence(
                decision_id=decision.id,
                evidence_type="technical",
                payload={"feature_version": "1.0.0"},
                created_at=timestamp,
                updated_at=timestamp,
            ),
        ]
    )
    risk = RiskEvaluation(
        decision_id=decision.id,
        approved=action == "BUY",
        position_size=Decimal(qty if action == "BUY" else 0),
        monetary_risk=(entry - stop) * qty if action == "BUY" else 0,
        payload={
            "engine_version": "2.0.0",
            "rules": [rule.__dict__ for rule in rules],
            "reason_codes": codes,
        },
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(risk)
    session.flush()
    config_version = int(setting(session, "risk_config", {}).get("version", 1))
    session.add_all(
        [
            RiskRuleResult(
                risk_evaluation_id=risk.id,
                configuration_version=config_version,
                rule_name=rule.rule_name,
                rule_version="1.0",
                threshold=rule.threshold,
                observed=rule.observed,
                unit="",
                passed=rule.passed,
                severity="error" if not rule.passed else "info",
                reason_code=rule.reason_code,
                message=rule.reason_code,
                evaluated_at=timestamp,
            )
            for rule in rules
        ]
    )
    if action == "BUY":
        approval = ApprovalRequest(
            decision_id=decision.id,
            status="pending",
            expires_at=decision.valid_until,
            version=1,
            payload={},
            created_at=timestamp,
            updated_at=timestamp,
        )
        session.add(approval)
        session.flush()
        decision.payload = {**decision.payload, "approval_id": approval.id}
    append(
        session,
        "decision",
        "trade_decision",
        decision.id,
        {"action": action, "reason_codes": codes},
        correlation,
    )
    return decision


def approve_and_fill(session: Session, approval_id: str, idem: str, correlation: str) -> Order:
    key_hash = hashlib.sha256(idem.encode()).hexdigest()
    approval = session.scalar(
        select(ApprovalRequest).where(ApprovalRequest.id == approval_id).with_for_update()
    )
    if not approval:
        raise ValueError("APPROVAL_NOT_FOUND")
    request_hash = hashlib.sha256(f"{approval_id}:BUY".encode()).hexdigest()
    existing = session.get(IdempotencyRecord, key_hash)
    if existing:
        if existing.request_hash != request_hash:
            raise ValueError("IDEMPOTENCY_CONFLICT")
        order = session.get(Order, existing.order_id)
        if order is None:
            raise ValueError("ORDER_NOT_FOUND")
        return order
    linked = session.scalar(select(Order).where(Order.approval_id == approval_id))
    if linked:
        return linked
    if approval.status != "pending":
        raise ValueError("APPROVAL_NOT_PENDING")
    if approval.expires_at < utcnow():
        approval.status = "expired"
        raise ValueError("RECOMMENDATION_EXPIRED")
    if setting(session, "kill_switch", {"enabled": True})["enabled"]:
        raise ValueError("KILL_SWITCH_ACTIVE")
    decision = session.get(TradeDecision, approval.decision_id)
    if decision is None:
        raise ValueError("DECISION_NOT_FOUND")
    instrument = session.get(Instrument, decision.instrument_id)
    if instrument is None:
        raise ValueError("INSTRUMENT_NOT_ELIGIBLE")
    entry = Decimal(decision.payload["entry_zone"])
    qty = Decimal(decision.payload["position_size"])
    price = (entry * Decimal("1.0005")).quantize(Decimal("0.0001"))
    notional = (price * qty).quantize(Decimal("0.01"))
    brokerage = (notional * Decimal("0.0003")).quantize(Decimal("0.01"))
    tax = (notional * Decimal("0.0007")).quantize(Decimal("0.01"))
    if notional + brokerage + tax > cash_balance(session):
        raise ValueError("INSUFFICIENT_CASH")
    timestamp = utcnow()
    order = Order(
        approval_id=approval.id,
        instrument_id=instrument.id,
        side="BUY",
        status="filled",
        quantity=qty,
        filled_quantity=qty,
        average_price=price,
        charges=brokerage + tax,
        idempotency_key_hash=key_hash,
        request_hash=request_hash,
        payload={},
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(order)
    session.flush()
    session.add(
        IdempotencyRecord(
            key_hash=key_hash, request_hash=request_hash, order_id=order.id, created_at=timestamp
        )
    )
    event_id = f"fill:{order.id}:1"
    session.add(
        OrderEvent(
            order_id=order.id,
            event_type="filled",
            external_event_id=event_id,
            payload={},
            created_at=timestamp,
            updated_at=timestamp,
        )
    )
    trade = Trade(
        order_id=order.id,
        instrument_id=instrument.id,
        event_id=event_id,
        side="BUY",
        quantity=qty,
        price=price,
        charges=brokerage + tax,
        realised_pnl=0,
        payload={},
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(trade)
    position = session.scalar(
        select(Position).where(Position.instrument_id == instrument.id).with_for_update()
    )
    if (
        position
        and position.quantity > 0
        and not setting(session, "risk_config", {}).get("allow_position_averaging", False)
    ):
        raise ValueError("DUPLICATE_POSITION")
    if position:
        position.average_price = weighted_average(
            position.quantity, position.average_price, qty, price
        )
        position.quantity += qty
        position.current_price = entry
        position.charges += brokerage + tax
        position.version += 1
        position.updated_at = timestamp
    else:
        position = Position(
            instrument_id=instrument.id,
            quantity=qty,
            average_price=price,
            current_price=entry,
            realised_pnl=0,
            charges=brokerage + tax,
            version=1,
            payload={
                "entry_regime": decision.payload["regime"]["regime"],
                "strategy_version": decision.payload["strategy_version"],
                "stop_loss": decision.payload["stop_loss"],
                "target": decision.payload["target"],
                "intraday": True,
                "entry_decision_id": decision.id,
            },
            created_at=timestamp,
            updated_at=timestamp,
        )
        session.add(position)
    add_ledger(session, "BUY_DEBIT", -notional, "order", order.id, f"buy:{order.id}", correlation)
    add_ledger(
        session, "BROKERAGE", -brokerage, "order", order.id, f"brokerage:{order.id}", correlation
    )
    add_ledger(session, "TAX", -tax, "order", order.id, f"tax:{order.id}", correlation)
    approval.status = "approved"
    approval.updated_at = timestamp
    approval.version += 1
    append(
        session, "approval", "approval_request", approval.id, {"status": "approved"}, correlation
    )
    append(
        session, "fill", "order", order.id, {"price": str(price), "quantity": str(qty)}, correlation
    )
    session.flush()
    snapshot(session, correlation)
    return order


def exit_position(
    session: Session,
    position_id: str,
    quantity: Decimal | None,
    reason: str,
    correlation: str,
    failure_hook=None,
) -> Trade:
    position = session.scalar(select(Position).where(Position.id == position_id).with_for_update())
    if not position or position.quantity <= 0:
        raise ValueError("POSITION_NOT_FOUND")
    qty = quantity or position.quantity
    if qty <= 0 or qty > position.quantity:
        raise ValueError("SELL_QUANTITY_EXCEEDS_HOLDING")
    timestamp = utcnow()
    instrument = session.get(Instrument, position.instrument_id)
    if instrument is None:
        raise ValueError("INSTRUMENT_NOT_ELIGIBLE")
    price = (position.current_price * Decimal("0.9995")).quantize(Decimal("0.0001"))
    notional = (price * qty).quantize(Decimal("0.01"))
    brokerage = (notional * Decimal("0.0003")).quantize(Decimal("0.01"))
    tax = (notional * Decimal("0.0007")).quantize(Decimal("0.01"))
    allocated = (position.charges * (qty / position.quantity)).quantize(Decimal("0.01"))
    pnl = realised_pnl(qty, position.average_price, price, allocated, brokerage + tax)
    order = Order(
        approval_id=None,
        instrument_id=instrument.id,
        side="SELL",
        status="filled",
        quantity=qty,
        filled_quantity=qty,
        average_price=price,
        charges=brokerage + tax,
        idempotency_key_hash=hashlib.sha256(
            f"exit:{position.id}:{position.version}:{qty}".encode()
        ).hexdigest(),
        request_hash="manual-exit",
        payload={"exit_reason": reason},
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(order)
    session.flush()
    if failure_hook:
        failure_hook("AFTER_ORDER_FLUSH")
    event_id = f"exit:{position.id}:{position.version}:{qty}"
    session.add(
        OrderEvent(
            order_id=order.id,
            event_type="filled",
            external_event_id=event_id,
            payload={"exit_reason": reason},
            created_at=timestamp,
            updated_at=timestamp,
        )
    )
    trade = Trade(
        order_id=order.id,
        instrument_id=instrument.id,
        event_id=event_id,
        side="SELL",
        quantity=qty,
        price=price,
        charges=brokerage + tax,
        realised_pnl=pnl,
        payload={
            "exit_reason": reason,
            "trigger_price": str(position.current_price),
            "slippage": str(position.current_price - price),
            "entry_regime": position.payload.get("entry_regime"),
            "exit_regime": position.payload.get("entry_regime"),
            "strategy_version": position.payload.get("strategy_version"),
            "holding_seconds": int((timestamp - position.created_at).total_seconds()),
        },
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(trade)
    session.flush()
    if failure_hook:
        failure_hook("AFTER_FILL_FLUSH")
    position.quantity -= qty
    position.realised_pnl += pnl
    position.charges -= allocated
    position.version += 1
    position.updated_at = timestamp
    if position.quantity == 0:
        position.average_price = Decimal(0)
    add_ledger(session, "SELL_CREDIT", notional, "trade", trade.id, f"sell:{event_id}", correlation)
    add_ledger(
        session,
        "BROKERAGE",
        -brokerage,
        "trade",
        trade.id,
        f"exit-brokerage:{event_id}",
        correlation,
    )
    add_ledger(session, "TAX", -tax, "trade", trade.id, f"exit-tax:{event_id}", correlation)
    review = TradeReview(
        trade_id=trade.id,
        payload={
            "outcome": "win" if pnl > 0 else "loss",
            "realised_pnl": str(pnl),
            "exit_reason": reason,
        },
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(review)
    session.flush()
    append(
        session,
        "trade_exit",
        "trade",
        trade.id,
        {"realised_pnl": str(pnl), "reason": reason},
        correlation,
    )
    append(session, "trade_review", "trade_review", review.id, review.payload, correlation)
    session.flush()
    snapshot(session, correlation)
    return trade


def portfolio(session: Session) -> dict:
    rows = session.scalars(
        select(Position).where(Position.quantity > 0).order_by(Position.created_at)
    ).all()
    cash = cash_balance(session)
    market = sum((p.quantity * p.current_price for p in rows), Decimal(0))
    unreal = sum(((p.current_price - p.average_price) * p.quantity for p in rows), Decimal(0))
    realised = Decimal(
        session.scalar(
            select(func.coalesce(func.sum(Trade.realised_pnl), 0)).where(Trade.side == "SELL")
        )
        or 0
    )
    last = session.scalar(select(PortfolioSnapshot).order_by(PortfolioSnapshot.created_at.desc()))
    return {
        "cash": str(cash),
        "market_value": str(market),
        "portfolio_value": str(cash + market),
        "realised_pnl": str(realised),
        "unrealised_pnl": str(unreal),
        "positions": [position_dict(p, session) for p in rows],
        "reconciliation_status": reconcile(session)["status"],
        "last_snapshot_at": last.created_at.isoformat() if last else None,
    }


def position_dict(p: Position, session: Session) -> dict:
    instrument = session.get(Instrument, p.instrument_id)
    if instrument is None:
        raise ValueError("INSTRUMENT_NOT_ELIGIBLE")
    return {
        "id": p.id,
        "symbol": instrument.symbol,
        "quantity": str(p.quantity),
        "average_price": str(p.average_price),
        "current_price": str(p.current_price),
        "realised_pnl": str(p.realised_pnl),
        "charges": str(p.charges),
        "version": p.version,
    }


def order_dict(o: Order, session: Session) -> dict:
    instrument = session.get(Instrument, o.instrument_id)
    if instrument is None:
        raise ValueError("INSTRUMENT_NOT_ELIGIBLE")
    events = session.scalars(
        select(OrderEvent).where(OrderEvent.order_id == o.id).order_by(OrderEvent.created_at)
    ).all()
    return {
        "id": o.id,
        "symbol": instrument.symbol,
        "side": o.side,
        "status": o.status,
        "quantity": str(o.quantity),
        "filled_quantity": str(o.filled_quantity),
        "average_price": str(o.average_price) if o.average_price is not None else None,
        "charges": str(o.charges),
        "created_at": o.created_at.isoformat(),
        "events": [{"type": e.event_type, "at": e.created_at.isoformat()} for e in events],
    }


def decision_dict(d: TradeDecision, session: Session) -> dict:
    approval = session.scalar(select(ApprovalRequest).where(ApprovalRequest.decision_id == d.id))
    risk = session.scalar(select(RiskEvaluation).where(RiskEvaluation.decision_id == d.id))
    data = {
        "id": d.id,
        "action": d.action,
        "generated_at": d.created_at.isoformat(),
        "valid_until": d.valid_until.isoformat(),
        **d.payload,
    }
    if approval:
        data.update({"approval_id": approval.id, "approval_status": approval.status})
        order = session.scalar(select(Order).where(Order.approval_id == approval.id))
        data["linked_order_id"] = order.id if order else None
    data["risk"] = risk.payload if risk else None
    return data


def reconcile(session: Session) -> dict:
    balance = cash_balance(session)
    debits = Decimal(
        session.scalar(
            select(func.coalesce(func.sum(Trade.price * Trade.quantity + Trade.charges), 0)).where(
                Trade.side == "BUY"
            )
        )
        or 0
    )
    credits = Decimal(
        session.scalar(
            select(func.coalesce(func.sum(Trade.price * Trade.quantity - Trade.charges), 0)).where(
                Trade.side == "SELL"
            )
        )
        or 0
    )
    expected = Decimal("1000000") - debits + credits
    # Ledger entries are posted at paise precision; reconcile at the same precision
    # to avoid treating sub-paise multiplication residue as a cash mismatch.
    difference = (balance - expected.quantize(Decimal("0.01"))).quantize(Decimal("0.01"))
    return {
        # A one-paise boundary can arise from NUMERIC multiplication before each
        # individual ledger posting is rounded; treat that bounded residue as reconciled.
        "status": "ok" if abs(difference) <= Decimal("0.01") else "mismatch",
        "ledger_balance": str(balance),
        "expected_balance": str(expected),
        "difference": str(difference),
    }
