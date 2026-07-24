from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import append
from app.common.db import get_session
from app.common.models import (
    ApprovalRequest,
    AuditLog,
    CashLedger,
    Instrument,
    JobRun,
    Order,
    SystemSetting,
    Trade,
    TradeDecision,
    IntelligenceCandle,
    IntelligenceInstrument,
    IntelligenceProviderStatus,
    IntelligenceTradingSession,
    FeatureValue,
    EvidenceEvaluation,
    ExternalItem,
    ExternalClassification,
    ExternalIntelligenceReadiness,
    ExternalItemRelation,
    OpportunityRecord,
    OpportunityRule,
    OpportunityDiscoveryRun,
    ResearchSnapshot,
    MLDataset,
    MLLabelRecord,
    MLTrainingRun,
    MetricAggregationReport,
    RobustnessReport,
    ValidationDecisionRecord,
    ModelRegistryDefinition,
    ModelVersionRecord,
    ModelCandidateRecord,
    PromotionRequestRecord,
    ModelRoleAssignment,
    RegistryAuditReport,
    ModelLoadManifest,
    OfflinePredictionRecord,
)
from app.config import settings
from app.paper_trading.service import (
    approve_and_fill,
    decision_dict,
    exit_position,
    order_dict,
    portfolio,
    reconcile,
    scan,
    seed,
    utcnow,
)
from app.paper_trading.daily_pnl import DailyPnLService
from app.scheduler.service import ensure_jobs, list_jobs, run_job
from app.risk.config_service import get_config, update_config
from app.features import REGISTRY
from app.evidence.engine import REGISTRY as EVIDENCE_REGISTRY
from app.external_intelligence.engine import PROVIDERS


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        from app.common.db import SessionLocal

        with SessionLocal.begin() as session:
            seed(session)
            ensure_jobs(session)
    except Exception:
        # Readiness reports database failure; startup never fabricates fallback state.
        pass
    yield


app = FastAPI(title="Market AI", version="0.3.0", docs_url="/docs", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Correlation-ID"],
)
passwords = PasswordHasher()
DEMO_PASSWORD_HASH = passwords.hash(settings.demo_password)


@app.middleware("http")
async def correlation(request: Request, call_next):
    request.state.correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = request.state.correlation_id
    return response


def token(subject: str, minutes: int, token_type: str) -> str:
    return jwt.encode(
        {"sub": subject, "type": token_type, "exp": datetime.now(UTC) + timedelta(minutes=minutes)},
        settings.jwt_secret,
        algorithm="HS256",
    )


def authenticated(authorization: str = Header(default="")) -> str:
    try:
        scheme, value = authorization.split(" ", 1)
        payload = jwt.decode(value, settings.jwt_secret, algorithms=["HS256"])
        if scheme.lower() != "bearer" or payload.get("type") != "access":
            raise JWTError()
        return str(payload["sub"])
    except (ValueError, JWTError, KeyError) as exc:
        raise HTTPException(401, "Authentication required") from exc


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class Refresh(BaseModel):
    refresh_token: str


class DecisionRequest(BaseModel):
    instrument_id: str = "RELIANCE"


class ExitRequest(BaseModel):
    quantity: Decimal | None = Field(default=None, gt=0)
    reason: str = Field(default="manual", pattern="^(manual|stop_loss|target|expiry|end_of_day)$")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "mode": "DEMO" if settings.demo_mode else "REAL",
        "trading_mode": "PAPER",
        "live_trading_enabled": False,
    }


@app.get("/readiness")
def readiness(session: Session = Depends(get_session)) -> dict:
    try:
        session.scalar(select(1))
        return {
            "status": "ready",
            "database": "connected",
            "safety_defaults": not settings.live_trading_enabled,
        }
    except Exception as exc:
        raise HTTPException(503, "Database unavailable") from exc


@app.post("/api/v1/auth/login")
def login(body: Login) -> dict:
    try:
        valid = body.username == settings.demo_username and passwords.verify(
            DEMO_PASSWORD_HASH, body.password
        )
    except VerifyMismatchError:
        valid = False
    if not valid:
        raise HTTPException(401, "Invalid credentials")
    return {
        "access_token": token(body.username, 30, "access"),
        "refresh_token": token(body.username, 480, "refresh"),
        "token_type": "bearer",
        "expires_in": 1800,
    }


@app.post("/api/v1/auth/refresh")
def refresh(body: Refresh) -> dict:
    try:
        payload = jwt.decode(body.refresh_token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise JWTError()
        return {
            "access_token": token(payload["sub"], 30, "access"),
            "token_type": "bearer",
            "expires_in": 1800,
        }
    except JWTError as exc:
        raise HTTPException(401, "Invalid refresh token") from exc


@app.get("/api/v1/system/status", dependencies=[Depends(authenticated)])
def status(session: Session = Depends(get_session)) -> dict:
    kill = session.get(SystemSetting, "kill_switch")
    return {
        "market": "simulated",
        "demo_mode": settings.demo_mode,
        "trading_mode": "PAPER",
        "live_trading_enabled": False,
        "kill_switch": kill.value["enabled"] if kill else True,
        "broker": "paper",
        "feed": "connected",
        "database": "connected",
        "worker": "durable-jobs",
        "scheduler": "healthy",
        "risk_config_version": get_config(session).get("version", 1),
    }


@app.post("/api/v1/system/kill-switch/{action}", dependencies=[Depends(authenticated)])
def kill_switch(action: str, request: Request, session: Session = Depends(get_session)) -> dict:
    if action not in {"enable", "disable"}:
        raise HTTPException(422, "action must be enable or disable")
    with session.begin():
        row = session.get(SystemSetting, "kill_switch", with_for_update=True)
        row.value = {"enabled": action == "enable"}
        row.version += 1
        row.updated_at = utcnow()
        append(
            session,
            "kill_switch_change",
            "system_setting",
            row.key,
            {"enabled": row.value["enabled"]},
            request.state.correlation_id,
        )
    return row.value


@app.get("/api/v1/instruments", dependencies=[Depends(authenticated)])
def instruments(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "id": x.id,
            "symbol": x.symbol,
            "exchange": x.exchange,
            "sector": x.sector,
            "eligible": x.eligible,
        }
        for x in session.scalars(select(Instrument).order_by(Instrument.symbol)).all()
    ]


@app.get("/api/v2/intelligence/instruments", dependencies=[Depends(authenticated)])
def intelligence_instruments(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "id": x.id,
            "exchange": x.exchange,
            "symbol": x.symbol,
            "exchange_token": x.exchange_token,
            "is_active": x.is_active,
            "valid_from": x.valid_from,
            "valid_to": x.valid_to,
            "metadata_version": x.metadata_version,
        }
        for x in session.scalars(
            select(IntelligenceInstrument).order_by(IntelligenceInstrument.symbol)
        ).all()
    ]


@app.get("/api/v2/intelligence/candles", dependencies=[Depends(authenticated)])
def intelligence_candles(instrument_id: str, session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(
        select(IntelligenceCandle)
        .where(IntelligenceCandle.instrument_id == instrument_id)
        .order_by(IntelligenceCandle.started_at)
    ).all()
    return [
        {
            "id": x.id,
            "interval": x.interval,
            "source": x.source,
            "open": x.open_price,
            "high": x.high_price,
            "low": x.low_price,
            "close": x.close_price,
            "volume": x.volume,
            "started_at": x.started_at,
            "ended_at": x.ended_at,
            "source_timestamp": x.source_timestamp,
            "received_at": x.received_at,
            "freshness_seconds": x.freshness_seconds,
            "revision": x.revision,
            "validation_status": x.validation_status,
        }
        for x in rows
    ]


@app.get("/api/v2/intelligence/sessions", dependencies=[Depends(authenticated)])
def intelligence_sessions(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "session_id": x.session_id,
            "session_date": x.session_date,
            "market_open": x.market_open,
            "market_close": x.market_close,
            "is_holiday": x.is_holiday,
            "is_half_session": x.is_half_session,
        }
        for x in session.scalars(
            select(IntelligenceTradingSession).order_by(IntelligenceTradingSession.session_date)
        ).all()
    ]


@app.get("/api/v2/intelligence/freshness", dependencies=[Depends(authenticated)])
def intelligence_freshness(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "provider": x.provider,
            "last_source_timestamp": x.last_source_timestamp,
            "last_received_at": x.last_received_at,
            "freshness_seconds": x.freshness_seconds,
            "status": x.status,
        }
        for x in session.scalars(
            select(IntelligenceProviderStatus).order_by(IntelligenceProviderStatus.provider)
        ).all()
    ]


@app.get("/api/v2/intelligence/providers", dependencies=[Depends(authenticated)])
def intelligence_providers(session: Session = Depends(get_session)) -> list[dict]:
    return intelligence_freshness(session)


@app.get("/api/v2/features", dependencies=[Depends(authenticated)])
def feature_values(
    instrument_id: str, session: Session = Depends(get_session), feature: str | None = None
) -> list[dict]:
    query = select(FeatureValue).where(FeatureValue.instrument_id == instrument_id)
    if feature:
        query = query.where(FeatureValue.feature_name == feature)
    return [
        {
            "instrument_id": x.instrument_id,
            "interval": x.interval,
            "observed_at": x.observed_at,
            "feature": x.feature_name,
            "version": x.feature_version,
            "value": x.value,
            "lineage": x.lineage,
        }
        for x in session.scalars(query.order_by(FeatureValue.observed_at)).all()
    ]


@app.get("/api/v2/features/available", dependencies=[Depends(authenticated)])
def available_features() -> list[dict]:
    return [vars(item) for item in REGISTRY.values()]


@app.get("/api/v2/evidence/available", dependencies=[Depends(authenticated)])
def available_evidence() -> list[dict]:
    return [vars(item) for item in EVIDENCE_REGISTRY.values()]


@app.get("/api/v2/evidence", dependencies=[Depends(authenticated)])
def evidence(
    instrument_id: str, session: Session = Depends(get_session), code: str | None = None
) -> list[dict]:
    query = select(EvidenceEvaluation).where(EvidenceEvaluation.instrument_id == instrument_id)
    if code:
        query = query.where(EvidenceEvaluation.evidence_code == code)
    return [
        {
            "id": x.id,
            "evidence_code": x.evidence_code,
            "direction": x.direction,
            "state": x.state,
            "strength": x.strength,
            "evaluation_time": x.evaluation_time,
            "expires_at": x.expires_at,
            "readiness": x.readiness,
            "inputs": x.inputs,
            "lineage": x.lineage,
        }
        for x in session.scalars(query.order_by(EvidenceEvaluation.evaluation_time)).all()
    ]


@app.get("/api/v2/data-readiness", dependencies=[Depends(authenticated)])
def data_readiness(instrument_id: str) -> dict:
    return {
        "instrument_id": instrument_id,
        "status": "unknown",
        "blocking_reasons": ["no_evaluation_context"],
    }


@app.get("/api/v1/scanner/results", dependencies=[Depends(authenticated)])
def scanner(session: Session = Depends(get_session)) -> list[dict]:
    return scan(session)


@app.post("/api/v1/scanner/run", dependencies=[Depends(authenticated)])
def scanner_run(session: Session = Depends(get_session)) -> list[dict]:
    return scan(session)


@app.post("/api/v1/decisions/generate", dependencies=[Depends(authenticated)])
def generate(
    body: DecisionRequest, request: Request, session: Session = Depends(get_session)
) -> dict:
    from app.paper_trading.service import generate_decision

    try:
        with session.begin():
            decision = generate_decision(
                session, body.instrument_id.upper(), request.state.correlation_id
            )
        return decision_dict(decision, session)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/v1/decisions", dependencies=[Depends(authenticated)])
def decisions(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> list[dict]:
    return [
        decision_dict(d, session)
        for d in session.scalars(
            select(TradeDecision)
            .order_by(TradeDecision.created_at.desc(), TradeDecision.id)
            .offset(offset)
            .limit(limit)
        ).all()
    ]


@app.get("/api/v1/decisions/{decision_id}", dependencies=[Depends(authenticated)])
def decision_one(decision_id: str, session: Session = Depends(get_session)) -> dict:
    row = session.get(TradeDecision, decision_id)
    if not row:
        raise HTTPException(404, "Decision not found")
    return decision_dict(row, session)


@app.get("/api/v1/approvals", dependencies=[Depends(authenticated)])
def approvals(
    status_filter: str | None = None, session: Session = Depends(get_session)
) -> list[dict]:
    query = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
    query = query.where(ApprovalRequest.status == status_filter) if status_filter else query
    return [
        {
            "id": a.id,
            "decision_id": a.decision_id,
            "status": a.status,
            "expires_at": a.expires_at.isoformat(),
            "version": a.version,
        }
        for a in session.scalars(query).all()
    ]


@app.post("/api/v1/approvals/{approval_id}/approve", dependencies=[Depends(authenticated)])
def approve(
    approval_id: str,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    session: Session = Depends(get_session),
) -> dict:
    try:
        with session.begin():
            order = approve_and_fill(
                session, approval_id, idempotency_key, request.state.correlation_id
            )
        return order_dict(order, session)
    except (ValueError, IntegrityError) as exc:
        raise HTTPException(409, str(getattr(exc, "orig", exc))) from exc


@app.post("/api/v1/approvals/{approval_id}/reject", dependencies=[Depends(authenticated)])
def reject(approval_id: str, request: Request, session: Session = Depends(get_session)) -> dict:
    with session.begin():
        row = session.scalar(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_id).with_for_update()
        )
        if not row:
            raise HTTPException(404, "Approval not found")
        if row.status != "pending":
            raise HTTPException(409, "APPROVAL_NOT_PENDING")
        row.status = "rejected"
        row.updated_at = utcnow()
        row.version += 1
        append(
            session,
            "rejection",
            "approval_request",
            row.id,
            {"status": "rejected"},
            request.state.correlation_id,
        )
    return {"id": row.id, "status": row.status}


@app.get("/api/v1/paper/orders", dependencies=[Depends(authenticated)])
def orders(limit: int = Query(100, le=500), session: Session = Depends(get_session)) -> list[dict]:
    return [
        order_dict(o, session)
        for o in session.scalars(select(Order).order_by(Order.created_at.desc()).limit(limit)).all()
    ]


@app.get("/api/v1/paper/orders/{order_id}", dependencies=[Depends(authenticated)])
def order_one(order_id: str, session: Session = Depends(get_session)) -> dict:
    row = session.get(Order, order_id)
    if not row:
        raise HTTPException(404, "Order not found")
    return order_dict(row, session)


@app.post("/api/v1/paper/orders/{order_id}/cancel", dependencies=[Depends(authenticated)])
def cancel(order_id: str, session: Session = Depends(get_session)) -> dict:
    with session.begin():
        row = session.get(Order, order_id, with_for_update=True)
        if not row:
            raise HTTPException(404, "Order not found")
        if row.status not in {"pending", "open", "partially_filled"}:
            raise HTTPException(409, "ORDER_NOT_CANCELLABLE")
        row.status = "cancelled"
        row.updated_at = utcnow()
    return order_dict(row, session)


@app.get("/api/v1/paper/positions", dependencies=[Depends(authenticated)])
def positions(session: Session = Depends(get_session)) -> list[dict]:
    return portfolio(session)["positions"]


@app.post("/api/v1/paper/positions/{position_id}/exit", dependencies=[Depends(authenticated)])
def position_exit(
    position_id: str, body: ExitRequest, request: Request, session: Session = Depends(get_session)
) -> dict:
    try:
        with session.begin():
            trade = exit_position(
                session, position_id, body.quantity, body.reason, request.state.correlation_id
            )
        return {
            "id": trade.id,
            "side": trade.side,
            "quantity": str(trade.quantity),
            "price": str(trade.price),
            "charges": str(trade.charges),
            "realised_pnl": str(trade.realised_pnl),
            **trade.payload,
        }
    except (ValueError, IntegrityError) as exc:
        raise HTTPException(409, str(getattr(exc, "orig", exc))) from exc


@app.get("/api/v1/paper/trades", dependencies=[Depends(authenticated)])
def trades(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "id": t.id,
            "side": t.side,
            "quantity": str(t.quantity),
            "price": str(t.price),
            "charges": str(t.charges),
            "realised_pnl": str(t.realised_pnl),
            "created_at": t.created_at.isoformat(),
            **t.payload,
        }
        for t in session.scalars(select(Trade).order_by(Trade.created_at.desc())).all()
    ]


@app.get("/api/v1/paper/portfolio", dependencies=[Depends(authenticated)])
def get_portfolio(session: Session = Depends(get_session)) -> dict:
    return portfolio(session)


@app.get("/api/v1/paper/daily-pnl", dependencies=[Depends(authenticated)])
def daily_pnl(session: Session = Depends(get_session)) -> dict:
    return DailyPnLService(session).calculate()


@app.get("/api/v1/paper/cash-ledger", dependencies=[Depends(authenticated)])
def ledger(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "id": x.id,
            "entry_type": x.entry_type,
            "amount": str(x.amount),
            "source_type": x.source_type,
            "source_id": x.source_id,
            "created_at": x.created_at.isoformat(),
        }
        for x in session.scalars(select(CashLedger).order_by(CashLedger.created_at.desc())).all()
    ]


@app.post("/api/v1/paper/reconcile", dependencies=[Depends(authenticated)])
def reconcile_api(session: Session = Depends(get_session)) -> dict:
    return reconcile(session)


@app.post("/api/v1/paper/reset", dependencies=[Depends(authenticated)])
def reset_demo(session: Session = Depends(get_session)) -> dict:
    # Restart safety is the default; destructive demo reset is intentionally not automatic.
    raise HTTPException(409, "Use scripts/reset_demo.py with explicit operator confirmation")


@app.get("/api/v1/audit", dependencies=[Depends(authenticated)])
def audit(limit: int = Query(100, le=500), session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "id": x.id,
            "kind": x.event_type,
            "entity_type": x.entity_type,
            "entity_id": x.entity_id,
            "actor": x.actor,
            "timestamp": x.occurred_at.isoformat(),
            "correlation_id": x.correlation_id,
            "payload": x.metadata_json,
        }
        for x in session.scalars(
            select(AuditLog).order_by(AuditLog.occurred_at.desc(), AuditLog.id).limit(limit)
        ).all()
    ]


@app.get("/api/v1/jobs", dependencies=[Depends(authenticated)])
def jobs(session: Session = Depends(get_session)) -> list[dict]:
    return list_jobs(session) + [
        {
            "id": x.id,
            "job_name": x.job_name,
            "status": x.status,
            "created_at": x.created_at.isoformat(),
        }
        for x in session.scalars(select(JobRun).order_by(JobRun.created_at.desc()).limit(100)).all()
    ]


@app.get("/api/v1/system/jobs/status", dependencies=[Depends(authenticated)])
def jobs_status(session: Session = Depends(get_session)) -> list[dict]:
    return list_jobs(session)


class JobRunRequest(BaseModel):
    job_type: str


@app.post("/api/v1/system/jobs/{job_type}/run", dependencies=[Depends(authenticated)])
def run_job_api(job_type: str, session: Session = Depends(get_session)) -> dict:
    try:
        with session.begin():
            return run_job(session, job_type)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/v1/risk/config", dependencies=[Depends(authenticated)])
def risk_config(session: Session = Depends(get_session)) -> dict:
    return get_config(session)


@app.get("/api/v2/external/items", dependencies=[Depends(authenticated)])
def external_items(
    session: Session = Depends(get_session), provider: str | None = None
) -> list[dict]:
    query = select(ExternalItem)
    if provider:
        query = query.where(ExternalItem.provider == provider)
    return [
        {
            "id": row.id,
            "provider": row.provider,
            "title": row.title,
            "canonical_identity": row.canonical_identity,
            "canonical_url": row.canonical_url,
            "published_at": row.published_at,
        }
        for row in session.scalars(query.order_by(ExternalItem.published_at.desc())).all()
    ]


@app.get("/api/v2/external/providers", dependencies=[Depends(authenticated)])
def external_providers() -> list[dict]:
    return [
        {"provider_code": code, **metadata, "enabled": False, "availability": "unavailable"}
        for code, metadata in PROVIDERS.items()
    ]


@app.get("/api/v2/external/classifications", dependencies=[Depends(authenticated)])
def external_classifications(
    external_item_id: str, session: Session = Depends(get_session)
) -> list[dict]:
    rows = session.scalars(
        select(ExternalClassification)
        .where(ExternalClassification.external_item_id == external_item_id)
        .order_by(ExternalClassification.evaluated_at.desc())
    ).all()
    return [
        {
            "category": x.category_code,
            "impact": x.impact,
            "confirmation": x.confirmation,
            "importance": x.importance_level,
            "signals": x.importance_signals,
            "evaluated_at": x.evaluated_at,
        }
        for x in rows
    ]


@app.get("/api/v2/external/readiness", dependencies=[Depends(authenticated)])
def external_readiness(provider: str, session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(
        select(ExternalIntelligenceReadiness)
        .where(ExternalIntelligenceReadiness.provider == provider)
        .order_by(ExternalIntelligenceReadiness.evaluated_at.desc())
    ).all()
    return [
        {
            "provider": x.provider,
            "status": x.status,
            "blocking_reasons": x.blocking_reasons,
            "warning_reasons": x.warning_reasons,
            "evaluated_at": x.evaluated_at,
            "expires_at": x.expires_at,
        }
        for x in rows
    ]


@app.get("/api/v2/external/relations", dependencies=[Depends(authenticated)])
def external_relations(item_id: str, session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(
        select(ExternalItemRelation)
        .where(
            (ExternalItemRelation.source_item_id == item_id)
            | (ExternalItemRelation.target_item_id == item_id)
        )
        .order_by(ExternalItemRelation.evaluated_at.desc())
    ).all()
    return [
        {
            "source_item_id": x.source_item_id,
            "target_item_id": x.target_item_id,
            "relation_type": x.relation_type,
            "rule_version": x.rule_version,
            "evaluated_at": x.evaluated_at,
            "details": x.details,
        }
        for x in rows
    ]


@app.get("/api/v2/opportunities", dependencies=[Depends(authenticated)])
def opportunities(
    instrument_id: str | None = None, session: Session = Depends(get_session)
) -> list[dict]:
    query = select(OpportunityRecord)
    if instrument_id:
        query = query.where(OpportunityRecord.instrument_id == instrument_id)
    rows = session.scalars(query.order_by(OpportunityRecord.evaluated_at.desc())).all()
    return [
        {
            "id": row.id,
            "instrument_id": row.instrument_id,
            "evaluated_at": row.evaluated_at,
            "expires_at": row.expires_at,
            "orientation": row.orientation,
            "state": row.state,
            "score": row.score,
            "rule_version": row.rule_version,
            "blockers": row.blockers,
            "cautions": row.cautions,
            "contributions": row.contributions,
            "lineage": row.lineage,
        }
        for row in rows
    ]


@app.get("/api/v2/opportunities/readiness", dependencies=[Depends(authenticated)])
def opportunity_readiness(
    instrument_id: str | None = None, session: Session = Depends(get_session)
) -> list[dict]:
    """Expose persisted research readiness; this never authorizes trading."""
    query = select(OpportunityRecord)
    if instrument_id:
        query = query.where(OpportunityRecord.instrument_id == instrument_id)
    rows = session.scalars(query.order_by(OpportunityRecord.evaluated_at.desc())).all()
    return [
        {
            "instrument_id": row.instrument_id,
            "evaluated_at": row.evaluated_at,
            "status": "not_ready" if row.blockers else "ready",
            "blocking_reasons": row.blockers,
            "warning_reasons": row.cautions,
            "valid_until": row.expires_at,
            "rule_version": row.rule_version,
        }
        for row in rows
    ]


@app.get("/api/v2/opportunities/rules", dependencies=[Depends(authenticated)])
def opportunity_rules(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "rule_code": x.rule_code,
            "display_name": x.display_name,
            "category": x.category,
            "rule_version": x.rule_version,
            "enabled": x.enabled,
            "parameters": x.parameters,
        }
        for x in session.scalars(
            select(OpportunityRule).order_by(
                OpportunityRule.rule_code, OpportunityRule.rule_version
            )
        ).all()
    ]


@app.get("/api/v2/opportunities/runs", dependencies=[Depends(authenticated)])
def opportunity_runs(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "id": x.id,
            "evaluated_at": x.evaluated_at,
            "rule_version": x.rule_version,
            "status": x.status,
            "instrument_count": x.instrument_count,
            "opportunity_count": x.opportunity_count,
            "lineage": x.lineage,
        }
        for x in session.scalars(
            select(OpportunityDiscoveryRun).order_by(OpportunityDiscoveryRun.evaluated_at.desc())
        ).all()
    ]


@app.get("/api/v2/research/snapshots", dependencies=[Depends(authenticated)])
def research_snapshots(
    instrument_id: str | None = None, session: Session = Depends(get_session)
) -> list[dict]:
    query = select(ResearchSnapshot)
    if instrument_id:
        query = query.where(ResearchSnapshot.instrument_id == instrument_id)
    rows = session.scalars(query.order_by(ResearchSnapshot.evaluated_at.desc())).all()
    return [row.payload for row in rows]


@app.get("/api/v2/research/snapshots/{snapshot_identity}", dependencies=[Depends(authenticated)])
def research_snapshot(snapshot_identity: str, session: Session = Depends(get_session)) -> dict:
    row = session.scalar(
        select(ResearchSnapshot).where(ResearchSnapshot.snapshot_identity == snapshot_identity)
    )
    if row is None:
        raise HTTPException(404, "Research snapshot not found")
    return row.payload


@app.get("/api/v3/datasets", dependencies=[Depends(authenticated)])
def ml_datasets(
    dataset_code: str | None = None, session: Session = Depends(get_session)
) -> list[dict]:
    query = select(MLDataset)
    if dataset_code:
        query = query.where(MLDataset.dataset_code == dataset_code)
    return [
        row.manifest for row in session.scalars(query.order_by(MLDataset.created_at.desc())).all()
    ]


@app.get("/api/v3/datasets/{dataset_identity}", dependencies=[Depends(authenticated)])
def ml_dataset(dataset_identity: str, session: Session = Depends(get_session)) -> dict:
    row = session.scalar(select(MLDataset).where(MLDataset.dataset_identity == dataset_identity))
    if row is None:
        raise HTTPException(404, "Dataset not found")
    return row.payload


@app.get("/api/v3/datasets/{dataset_identity}/quality", dependencies=[Depends(authenticated)])
def ml_dataset_quality(dataset_identity: str, session: Session = Depends(get_session)) -> dict:
    from app.datasets.builder import dataset_quality

    row = session.scalar(select(MLDataset).where(MLDataset.dataset_identity == dataset_identity))
    if row is None:
        raise HTTPException(404, "Dataset not found")
    return dataset_quality(row.payload)


@app.get("/api/v3/labels", dependencies=[Depends(authenticated)])
def ml_labels(status: str | None = None, session: Session = Depends(get_session)) -> list[dict]:
    query = select(MLLabelRecord)
    if status:
        query = query.where(MLLabelRecord.status == status)
    return [
        row.payload
        for row in session.scalars(query.order_by(MLLabelRecord.feature_cutoff_at)).all()
    ]


@app.get("/api/v3/labels/quality", dependencies=[Depends(authenticated)])
def ml_label_quality(session: Session = Depends(get_session)) -> dict:
    from app.labels.framework import label_quality

    rows = session.scalars(select(MLLabelRecord)).all()
    return label_quality([row.payload.get("label", row.payload) for row in rows])


@app.get("/api/v3/ml/training-runs", dependencies=[Depends(authenticated)])
def ml_training_runs(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "training_identity": row.training_identity,
            "dataset_identity": row.dataset_identity,
            "label_spec": row.label_spec,
            "algorithm": row.algorithm,
            "status": row.status,
            "metrics": row.metrics,
            "research_only": row.research_only,
        }
        for row in session.scalars(
            select(MLTrainingRun).order_by(MLTrainingRun.created_at.desc())
        ).all()
    ]


@app.get("/api/v3/ml/metric-reports", dependencies=[Depends(authenticated)])
def metric_reports(session: Session = Depends(get_session)) -> list[dict]:
    return [
        row.payload
        for row in session.scalars(
            select(MetricAggregationReport).order_by(MetricAggregationReport.created_at.desc())
        ).all()
    ]


@app.get("/api/v3/ml/robustness-reports", dependencies=[Depends(authenticated)])
def robustness_reports(session: Session = Depends(get_session)) -> list[dict]:
    return [
        row.payload
        for row in session.scalars(
            select(RobustnessReport).order_by(RobustnessReport.created_at.desc())
        ).all()
    ]


@app.get("/api/v3/ml/validation-decisions", dependencies=[Depends(authenticated)])
def validation_decisions(session: Session = Depends(get_session)) -> list[dict]:
    return [
        row.payload
        for row in session.scalars(
            select(ValidationDecisionRecord).order_by(ValidationDecisionRecord.created_at.desc())
        ).all()
    ]


@app.get("/api/v3/model-registry/definitions", dependencies=[Depends(authenticated)])
def model_registry_definitions(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "definition_identity": row.definition_identity,
            "definition_code": row.definition_code,
            "definition_version": row.definition_version,
            "definition_type": row.definition_type,
            "payload": row.payload,
            "enabled": row.enabled,
        }
        for row in session.scalars(
            select(ModelRegistryDefinition).order_by(ModelRegistryDefinition.definition_code)
        ).all()
    ]


@app.get("/api/v3/model-registry/versions", dependencies=[Depends(authenticated)])
def model_registry_versions(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "version_identity": row.version_identity,
            "namespace": row.namespace,
            "model_code": row.model_code,
            "semantic_version": row.semantic_version,
            "package_identity": row.package_identity,
            "predecessor_identity": row.predecessor_identity,
        }
        for row in session.scalars(
            select(ModelVersionRecord).order_by(ModelVersionRecord.created_at.desc())
        ).all()
    ]


@app.get("/api/v3/model-registry/candidates", dependencies=[Depends(authenticated)])
def model_registry_candidates(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "candidate_identity": row.candidate_identity,
            "version_identity": row.version_identity,
            "status": row.status,
            "payload": row.payload,
            "lineage": row.lineage,
        }
        for row in session.scalars(
            select(ModelCandidateRecord).order_by(ModelCandidateRecord.created_at.desc())
        ).all()
    ]


@app.get("/api/v3/model-registry/promotion-requests", dependencies=[Depends(authenticated)])
def promotion_requests(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "request_identity": row.request_identity,
            "candidate_identity": row.candidate_identity,
            "stage": row.stage,
            "decision": row.decision,
            "payload": row.payload,
            "lineage": row.lineage,
        }
        for row in session.scalars(
            select(PromotionRequestRecord).order_by(PromotionRequestRecord.created_at.desc())
        ).all()
    ]


@app.get("/api/v3/model-registry/role-assignments", dependencies=[Depends(authenticated)])
def role_assignments(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "assignment_identity": row.assignment_identity,
            "scope": row.scope,
            "champion_identity": row.champion_identity,
            "challenger_identities": row.challenger_identities,
            "status": row.status,
            "payload": row.payload,
        }
        for row in session.scalars(
            select(ModelRoleAssignment).order_by(ModelRoleAssignment.created_at.desc())
        ).all()
    ]


@app.get("/api/v3/model-registry/audit-reports", dependencies=[Depends(authenticated)])
def registry_audit_reports(session: Session = Depends(get_session)) -> list[dict]:
    return [
        row.payload
        for row in session.scalars(
            select(RegistryAuditReport).order_by(RegistryAuditReport.created_at.desc())
        ).all()
    ]


@app.get("/api/v3/model-loading/manifests", dependencies=[Depends(authenticated)])
def model_load_manifests(session: Session = Depends(get_session)) -> list[dict]:
    return [
        row.payload
        for row in session.scalars(
            select(ModelLoadManifest).order_by(ModelLoadManifest.created_at.desc())
        ).all()
    ]


@app.get("/api/v3/model-loading/offline-predictions", dependencies=[Depends(authenticated)])
def offline_predictions(session: Session = Depends(get_session)) -> list[dict]:
    return [
        row.payload
        for row in session.scalars(
            select(OfflinePredictionRecord).order_by(OfflinePredictionRecord.created_at.desc())
        ).all()
    ]


class RiskConfigUpdate(BaseModel):
    values: dict = Field(default_factory=dict)
    reason: str = Field(min_length=3, max_length=300)


@app.put("/api/v1/risk/config", dependencies=[Depends(authenticated)])
def risk_config_update(
    body: RiskConfigUpdate, request: Request, session: Session = Depends(get_session)
) -> dict:
    with session.begin():
        result = update_config(session, body.values, body.reason, "local-user")
        append(
            session,
            "risk_configuration_change",
            "system_setting",
            "risk_config",
            {"version": result["version"], "reason": body.reason},
            request.state.correlation_id,
        )
    return result


@app.get("/api/v1/alerts", dependencies=[Depends(authenticated)])
def alerts(session: Session = Depends(get_session)) -> list[dict]:
    return (
        []
        if reconcile(session)["status"] == "ok"
        else [{"severity": "critical", "code": "LEDGER_RECONCILIATION_FAILED"}]
    )


@app.websocket("/api/v1/ws/market")
async def market_ws(ws: WebSocket):
    await ws.accept()
    while True:
        from app.common.db import SessionLocal

        with SessionLocal() as session:
            quotes = scan(session)[:5]
        await ws.send_json(
            {"type": "quotes", "at": datetime.now(UTC).isoformat(), "quotes": quotes}
        )
        await asyncio.sleep(2)
