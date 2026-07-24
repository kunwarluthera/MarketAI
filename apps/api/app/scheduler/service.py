from __future__ import annotations

from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import (
    ApprovalRequest,
    Alert,
    Instrument,
    JobRun,
    MarketCandle,
    MarketSnapshot,
    FeatureSnapshot,
    MarketRegime,
    Position,
    Trade,
    TradeReview,
    ScheduledJob,
    TradeCandidate,
    TradeDecision,
)
from app.domain import Candle, features
from decimal import Decimal
from random import Random
from app.paper_trading.service import exit_position, generate_decision, reconcile, snapshot, utcnow
from app.scheduler.eod_policy import EodExitPolicy, RetryableEodExitError

JOB_TYPES = (
    "SIMULATED_PRICE_UPDATE",
    "CANDLE_FINALISATION",
    "FEATURE_REFRESH",
    "MARKET_REGIME_REFRESH",
    "DECISION_SCAN",
    "RECOMMENDATION_EXPIRY",
    "APPROVAL_EXPIRY",
    "STOP_TARGET_EVALUATION",
    "EOD_POSITION_EXIT",
    "PORTFOLIO_SNAPSHOT",
    "LEDGER_RECONCILIATION",
    "TRADE_REVIEW_CREATION",
    "STALE_DATA_CHECK",
    "SYSTEM_HEALTH_CHECK",
    "AUDIT_RETENTION_CHECK",
)


def ensure_jobs(session: Session) -> None:
    timestamp = utcnow()
    existing = {j.job_type for j in session.scalars(select(ScheduledJob)).all()}
    for job_type in JOB_TYPES:
        if job_type not in existing:
            session.add(
                ScheduledJob(
                    job_type=job_type,
                    enabled=True,
                    interval_seconds=60,
                    next_run_at=timestamp,
                    status="idle",
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
    session.flush()


def list_jobs(session: Session) -> list[dict]:
    ensure_jobs(session)
    return [
        {
            "id": j.id,
            "job_type": j.job_type,
            "enabled": j.enabled,
            "interval_seconds": j.interval_seconds,
            "next_run_at": j.next_run_at.isoformat(),
            "last_run_at": j.last_run_at.isoformat() if j.last_run_at else None,
            "last_success_at": j.last_success_at.isoformat() if j.last_success_at else None,
            "last_failure_at": j.last_failure_at.isoformat() if j.last_failure_at else None,
            "status": j.status,
            "retry_count": j.retry_count,
            "lease_expires_at": j.lease_expires_at.isoformat() if j.lease_expires_at else None,
            "heartbeat_at": j.heartbeat_at.isoformat() if j.heartbeat_at else None,
        }
        for j in session.scalars(select(ScheduledJob).order_by(ScheduledJob.job_type)).all()
    ]


def run_job(
    session: Session,
    job_type: str,
    worker_id: str = "api-manual",
    evaluation_time=None,
    eod_policy=None,
    exit_executor=None,
) -> dict:
    ensure_jobs(session)
    job = session.scalar(
        select(ScheduledJob).where(ScheduledJob.job_type == job_type).with_for_update()
    )
    if not job:
        raise ValueError("JOB_NOT_FOUND")
    if not job.enabled:
        raise ValueError("JOB_DISABLED")
    timestamp = evaluation_time or utcnow()
    policy = eod_policy or EodExitPolicy()
    correlation = str(uuid4())
    (
        job.status,
        job.lock_owner,
        job.lock_acquired_at,
        job.lease_expires_at,
        job.heartbeat_at,
        job.last_run_at,
    ) = (
        "running",
        worker_id,
        timestamp,
        timestamp + timedelta(seconds=60),
        timestamp,
        timestamp,
    )
    run = JobRun(
        job_key=f"{job_type}:{timestamp.isoformat()}:{uuid4()}",
        job_name=job_type,
        status="running",
        payload={"correlation_id": correlation, "worker_id": worker_id},
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(run)
    session.flush()
    try:
        result = {
            "status": "skipped",
            "rows_affected": 0,
            "entities_created": [],
            "entities_updated": [],
            "warnings": [],
            "reason_codes": [],
            "safe_summary": {},
        }
        if job_type == "SIMULATED_PRICE_UPDATE":
            seed = int(job.payload.get("seed", 42))
            scenario = job.payload.get("scenario", "TRENDING_UP")
            rng = Random(seed)
            count = 0
            for instrument in session.scalars(
                select(Instrument).where(Instrument.eligible.is_(True))
            ).all():
                previous = session.scalar(
                    select(MarketSnapshot)
                    .where(MarketSnapshot.instrument_id == instrument.id)
                    .order_by(MarketSnapshot.exchange_timestamp.desc())
                )
                base = previous.price if previous else Decimal("100")
                change = Decimal(str(rng.uniform(0.0001, 0.002))) * base
                if scenario == "TRENDING_DOWN":
                    change = -change
                if scenario == "SIDEWAYS":
                    change = Decimal("0")
                price = (base + change).quantize(Decimal("0.0001"))
                occurrence = f"{job_type}:{job.next_run_at.isoformat()}"
                if not session.scalar(
                    select(MarketSnapshot).where(
                        MarketSnapshot.instrument_id == instrument.id,
                        MarketSnapshot.occurrence_key == occurrence,
                    )
                ):
                    session.add(
                        MarketSnapshot(
                            instrument_id=instrument.id,
                            price=price,
                            volume=10000,
                            exchange_timestamp=timestamp,
                            ingested_at=timestamp,
                            source="simulated",
                            scenario=scenario,
                            occurrence_key=occurrence,
                            created_at=timestamp,
                            updated_at=timestamp,
                        )
                    )
                    count += 1
            result = {
                **result,
                "status": "succeeded",
                "rows_affected": count,
                "safe_summary": {"scenario": scenario, "seed": seed},
            }
        elif job_type == "CANDLE_FINALISATION":
            count = 0
            for instrument in session.scalars(
                select(Instrument).where(Instrument.eligible.is_(True))
            ).all():
                snaps = session.scalars(
                    select(MarketSnapshot)
                    .where(MarketSnapshot.instrument_id == instrument.id)
                    .order_by(MarketSnapshot.exchange_timestamp)
                ).all()
                if not snaps:
                    continue
                candle = MarketCandle(
                    instrument_id=instrument.id,
                    interval="1m",
                    open=snaps[0].price,
                    high=max(s.price for s in snaps),
                    low=min(s.price for s in snaps),
                    close=snaps[-1].price,
                    volume=sum(s.volume for s in snaps),
                    started_at=snaps[0].exchange_timestamp.replace(second=0, microsecond=0),
                    completed_at=timestamp,
                    source="simulated",
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                if not session.scalar(
                    select(MarketCandle).where(
                        MarketCandle.instrument_id == instrument.id,
                        MarketCandle.interval == "1m",
                        MarketCandle.started_at == candle.started_at,
                    )
                ):
                    session.add(candle)
                    count += 1
            result = {**result, "status": "succeeded", "rows_affected": count}
        elif job_type == "FEATURE_REFRESH":
            count = 0
            for instrument in session.scalars(
                select(Instrument).where(Instrument.eligible.is_(True))
            ).all():
                rows = session.scalars(
                    select(MarketCandle)
                    .where(MarketCandle.instrument_id == instrument.id)
                    .order_by(MarketCandle.started_at)
                ).all()
                if not rows:
                    continue
                calc = features(
                    [
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
                )
                session.add(
                    __import__("app.common.models", fromlist=["FeatureSnapshot"]).FeatureSnapshot(
                        instrument_id=instrument.id,
                        valid_until=timestamp + timedelta(minutes=5),
                        version="1.0.0",
                        payload={
                            k: str(v) if isinstance(v, Decimal) else v for k, v in calc.items()
                        },
                        created_at=timestamp,
                        updated_at=timestamp,
                    )
                )
                count += 1
            result = {**result, "status": "succeeded", "rows_affected": count}
        elif job_type == "MARKET_REGIME_REFRESH":
            count = 0
            for feature in session.scalars(select(FeatureSnapshot)).all():
                values = feature.payload or {}
                if not values.get("ready") or values.get("quality") != "valid":
                    value, confidence = "weak_or_invalid_data", 0
                elif Decimal(str(values.get("price_vs_vwap", 0))) > 0:
                    value, confidence = "trending_up", 82
                elif Decimal(str(values.get("price_vs_vwap", 0))) < 0:
                    value, confidence = "trending_down", 78
                else:
                    value, confidence = "sideways", 60
                existing = [
                    r
                    for r in session.scalars(
                        select(MarketRegime).where(
                            MarketRegime.instrument_id == feature.instrument_id
                        )
                    ).all()
                    if (r.payload or {}).get("source_feature_id") == feature.id
                ]
                if existing:
                    continue
                session.add(
                    MarketRegime(
                        instrument_id=feature.instrument_id,
                        regime=value,
                        valid_until=feature.valid_until,
                        payload={"source_feature_id": feature.id, "confidence": confidence},
                        created_at=timestamp,
                        updated_at=timestamp,
                    )
                )
                count += 1
            result = {**result, "status": "succeeded", "rows_affected": count}
        elif job_type == "DECISION_SCAN":
            count = 0
            for instrument in session.scalars(
                select(Instrument).where(Instrument.eligible.is_(True))
            ).all():
                try:
                    generate_decision(session, instrument.symbol, correlation)
                    count += 1
                except ValueError:
                    continue
            result = {**result, "status": "succeeded", "rows_affected": count}
        elif job_type in {
            "STOP_TARGET_EVALUATION",
            "EOD_POSITION_EXIT",
            "TRADE_REVIEW_CREATION",
            "STALE_DATA_CHECK",
        }:
            if job_type == "STOP_TARGET_EVALUATION":
                exits = 0
                for position in session.scalars(
                    select(Position).where(Position.quantity > 0).with_for_update()
                ).all():
                    row = session.scalar(
                        select(MarketSnapshot)
                        .where(MarketSnapshot.instrument_id == position.instrument_id)
                        .order_by(MarketSnapshot.exchange_timestamp.desc())
                    )
                    if not row:
                        continue
                    stop, target = position.payload.get("stop_loss"), position.payload.get("target")
                    latest_candle = session.scalar(
                        select(MarketCandle)
                        .where(
                            MarketCandle.instrument_id == position.instrument_id,
                            MarketCandle.completed_at <= timestamp,
                        )
                        .order_by(MarketCandle.started_at.desc())
                    )
                    stop_hit = bool(stop and row.price <= Decimal(str(stop)))
                    target_hit = bool(target and row.price >= Decimal(str(target)))
                    reason = None
                    trigger_price = row.price
                    if latest_candle and stop and target:
                        stop_hit = stop_hit or latest_candle.low <= Decimal(str(stop))
                        target_hit = target_hit or latest_candle.high >= Decimal(str(target))
                        if stop_hit and target_hit:
                            reason = "AMBIGUOUS_SAME_CANDLE_STOP_TARGET_CONSERVATIVE_STOP"
                            trigger_price = Decimal(str(stop))
                        elif stop_hit:
                            reason = "STOP_LOSS_TRIGGERED"
                            trigger_price = Decimal(str(stop))
                        elif target_hit:
                            reason = "TARGET_TRIGGERED"
                            trigger_price = Decimal(str(target))
                    elif stop_hit:
                        reason = "STOP_LOSS_TRIGGERED"
                    elif target_hit:
                        reason = "TARGET_TRIGGERED"
                    if reason:
                        position.current_price = trigger_price
                        position.payload = {
                            **position.payload,
                            "trigger_source_id": row.id,
                            "trigger_price": str(trigger_price),
                            "requested_exit_price": str(trigger_price),
                        }
                        exit_position(session, position.id, position.quantity, reason, correlation)
                        exits += 1
                result = {
                    **result,
                    "status": "succeeded",
                    "rows_affected": exits,
                    "safe_summary": {"exits_created": exits},
                }
            elif job_type == "EOD_POSITION_EXIT" and job.payload.get("force", False):
                local_time = timestamp.astimezone(policy.market_timezone)
                if (
                    not policy.is_trading_day(local_time.date())
                    or local_time.time() < policy.cutoff_time
                ):
                    result = {
                        **result,
                        "status": "succeeded",
                        "rows_affected": 0,
                        "reason_codes": ["EOD_NOT_ELIGIBLE"],
                    }
                    return result
                exits = 0
                for position in session.scalars(
                    select(Position).where(Position.quantity > 0)
                ).all():
                    if position.payload.get("intraday"):
                        row = session.scalar(
                            select(MarketSnapshot)
                            .where(MarketSnapshot.instrument_id == position.instrument_id)
                            .order_by(MarketSnapshot.exchange_timestamp.desc())
                        )
                        if row:
                            position.current_price = row.price
                            executor = exit_executor or exit_position
                            attempts = 0
                            while True:
                                attempts += 1
                                try:
                                    with session.begin_nested():
                                        executor(
                                            session,
                                            position.id,
                                            position.quantity,
                                            "EOD_FORCED_EXIT",
                                            correlation,
                                        )
                                    failure_key = f"EOD_EXIT_FAILED:{position.instrument_id}:{position.id}:{local_time.date().isoformat()}"
                                    failure_alert = session.scalar(
                                        select(Alert).where(
                                            Alert.issue_key == failure_key, Alert.status == "open"
                                        )
                                    )
                                    if failure_alert:
                                        failure_alert.status = "resolved"
                                        failure_alert.resolved_at = timestamp
                                        failure_alert.updated_at = timestamp
                                    break
                                except RetryableEodExitError as exc:
                                    if attempts >= policy.max_retry_attempts:
                                        key = f"EOD_EXIT_FAILED:{position.instrument_id}:{position.id}:{local_time.date().isoformat()}"
                                        alert = session.scalar(
                                            select(Alert).where(
                                                Alert.issue_key == key, Alert.status == "open"
                                            )
                                        )
                                        payload = {
                                            "position_id": position.id,
                                            "instrument_id": position.instrument_id,
                                            "attempt_count": attempts,
                                            "max_attempts": policy.max_retry_attempts,
                                            "failure_type": type(exc).__name__,
                                            "message": str(exc),
                                        }
                                        if alert:
                                            alert.last_detected_at = timestamp
                                            alert.updated_at = timestamp
                                            alert.payload = payload
                                        else:
                                            session.add(
                                                Alert(
                                                    alert_type="EOD_EXIT_FAILED",
                                                    issue_key=key,
                                                    severity="critical",
                                                    status="open",
                                                    reason_code="EOD_EXIT_FAILED",
                                                    instrument_id=position.instrument_id,
                                                    first_detected_at=timestamp,
                                                    last_detected_at=timestamp,
                                                    payload=payload,
                                                    created_at=timestamp,
                                                    updated_at=timestamp,
                                                )
                                            )
                                        break
                                    continue
                            exits += 1
                result = {**result, "status": "succeeded", "rows_affected": exits}
            elif job_type == "TRADE_REVIEW_CREATION":
                created = 0
                for trade in session.scalars(select(Trade).where(Trade.side == "SELL")).all():
                    if not session.scalar(
                        select(TradeReview).where(TradeReview.trade_id == trade.id)
                    ):
                        session.add(
                            TradeReview(
                                trade_id=trade.id,
                                payload={
                                    "exit_reason": trade.payload.get("exit_reason"),
                                    "realised_pnl": str(trade.realised_pnl),
                                },
                                created_at=timestamp,
                                updated_at=timestamp,
                            )
                        )
                        created += 1
                result = {**result, "status": "succeeded", "rows_affected": created}
            else:
                created = 0
                for instrument in session.scalars(
                    select(Instrument).where(Instrument.eligible.is_(True))
                ).all():
                    row = session.scalar(
                        select(MarketSnapshot)
                        .where(MarketSnapshot.instrument_id == instrument.id)
                        .order_by(MarketSnapshot.exchange_timestamp.desc())
                    )
                    key = f"MARKET_DATA_MISSING:{instrument.id}"
                    open_alert = session.scalar(
                        select(Alert).where(Alert.issue_key == key, Alert.status == "open")
                    )
                    if not row and not open_alert:
                        session.add(
                            Alert(
                                alert_type="MARKET_DATA_MISSING",
                                issue_key=key,
                                severity="critical",
                                status="open",
                                reason_code="DATA_MISSING",
                                instrument_id=instrument.id,
                                first_detected_at=timestamp,
                                last_detected_at=timestamp,
                                payload={},
                                created_at=timestamp,
                                updated_at=timestamp,
                            )
                        )
                        created += 1
                    elif not row and open_alert:
                        open_alert.last_detected_at = timestamp
                        open_alert.updated_at = timestamp
                    elif row and open_alert:
                        open_alert.status = "resolved"
                        open_alert.resolved_at = timestamp
                        open_alert.last_detected_at = timestamp
                        open_alert.updated_at = timestamp
                    if row and timestamp - row.exchange_timestamp > timedelta(minutes=5):
                        stale_key = f"MARKET_DATA_STALE:{instrument.id}"
                        stale_alert = session.scalar(
                            select(Alert).where(
                                Alert.issue_key == stale_key, Alert.status == "open"
                            )
                        )
                        if stale_alert:
                            stale_alert.last_detected_at = timestamp
                            stale_alert.updated_at = timestamp
                        else:
                            session.add(
                                Alert(
                                    alert_type="MARKET_DATA_STALE",
                                    issue_key=stale_key,
                                    severity="warning",
                                    status="open",
                                    reason_code="DATA_STALE",
                                    instrument_id=instrument.id,
                                    first_detected_at=timestamp,
                                    last_detected_at=timestamp,
                                    payload={
                                        "observed_at": row.exchange_timestamp.isoformat(),
                                        "max_age_seconds": 300,
                                    },
                                    created_at=timestamp,
                                    updated_at=timestamp,
                                )
                            )
                            created += 1
                    elif row:
                        stale_key = f"MARKET_DATA_STALE:{instrument.id}"
                        stale_alert = session.scalar(
                            select(Alert).where(
                                Alert.issue_key == stale_key, Alert.status == "open"
                            )
                        )
                        if stale_alert:
                            stale_alert.status = "resolved"
                            stale_alert.resolved_at = timestamp
                            stale_alert.last_detected_at = timestamp
                            stale_alert.updated_at = timestamp
                result = {
                    **result,
                    "status": "succeeded",
                    "rows_affected": created,
                    "reason_codes": ["STALE_CHECK_COMPLETED"],
                }
        elif job_type == "PORTFOLIO_SNAPSHOT":
            snapshot(session, correlation)
            result = {
                **result,
                "status": "succeeded",
                "rows_affected": 1,
                "safe_summary": {"snapshot": "created"},
            }
        elif job_type == "LEDGER_RECONCILIATION":
            result = reconcile(session)
            result = {
                **result,
                "status": "succeeded",
                "rows_affected": 1,
                "safe_summary": {"reconciliation": result},
            }
        elif job_type == "RECOMMENDATION_EXPIRY":
            candidates = session.scalars(
                select(TradeCandidate).where(TradeCandidate.valid_until < timestamp)
            ).all()
            for candidate in candidates:
                candidate.payload = {
                    **(candidate.payload or {}),
                    "status": "expired",
                    "reason_code": "RECOMMENDATION_EXPIRED",
                }
            decisions = session.scalars(
                select(TradeDecision).where(
                    TradeDecision.valid_until < timestamp, TradeDecision.action.in_(["BUY", "SELL"])
                )
            ).all()
            for decision in decisions:
                decision.action = "HOLD"
                decision.payload = {
                    **(decision.payload or {}),
                    "reason_codes": ["RECOMMENDATION_EXPIRED"],
                }
            count = len(candidates) + len(decisions)
            result = {
                **result,
                "status": "succeeded",
                "rows_affected": count,
                "reason_codes": ["RECOMMENDATION_EXPIRED"] if count else [],
            }
        elif job_type == "APPROVAL_EXPIRY":
            approvals = session.scalars(
                select(ApprovalRequest).where(
                    ApprovalRequest.status == "pending", ApprovalRequest.expires_at < timestamp
                )
            ).all()
            for approval in approvals:
                approval.status = "expired"
                approval.payload = {**(approval.payload or {}), "reason_code": "APPROVAL_EXPIRED"}
            count = len(approvals)
            result = {
                **result,
                "status": "succeeded",
                "rows_affected": count,
                "reason_codes": ["APPROVAL_EXPIRED"] if count else [],
            }
        elif job_type == "SYSTEM_HEALTH_CHECK":
            result = {
                **result,
                "status": "succeeded",
                "safe_summary": {"database": "connected", "worker": worker_id},
            }
        elif job_type == "AUDIT_RETENTION_CHECK":
            result = {
                **result,
                "status": "skipped",
                "reason_codes": ["SKIPPED_WITH_POLICY"],
                "safe_summary": {"destructive_retention": False},
            }
        run.payload = {**run.payload, "result": result}
        run.status = "success"
        job.status = "idle"
        job.last_success_at = timestamp
        job.next_run_at = timestamp + timedelta(seconds=job.interval_seconds)
        job.lock_owner = None
        job.lock_acquired_at = None
        job.lease_expires_at = None
        job.heartbeat_at = None
        job.updated_at = timestamp
        return {
            "job_type": job_type,
            "status": "success",
            "result": result,
            "run_id": run.id,
            "correlation_id": correlation,
        }
    except Exception as exc:
        run.status = "failed"
        run.payload = {**run.payload, "error": type(exc).__name__, "message": str(exc)[:200]}
        job.status = "failed"
        job.last_failure_at = timestamp
        job.retry_count += 1
        job.lock_owner = None
        job.lock_acquired_at = None
        job.lease_expires_at = None
        job.heartbeat_at = None
        job.next_run_at = timestamp + timedelta(
            seconds=min(300, 5 * (2 ** min(job.retry_count, 6)))
        )
        job.updated_at = timestamp
        run.payload = {
            **run.payload,
            "result": {
                "status": "failed",
                "rows_affected": 0,
                "entities_created": [],
                "entities_updated": [],
                "warnings": [str(exc)[:200]],
                "reason_codes": [type(exc).__name__],
                "safe_summary": {},
            },
        }
        return {
            "job_type": job_type,
            "status": "failed",
            "run_id": run.id,
            "correlation_id": correlation,
            "retry_at": job.next_run_at.isoformat(),
        }
