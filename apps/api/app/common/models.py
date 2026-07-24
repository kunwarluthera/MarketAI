from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

MONEY = Numeric(20, 4)
QTY = Numeric(20, 6)


def uid() -> str:
    return str(uuid.uuid4())


class Timed:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Instrument(Base, Timed):
    __tablename__ = "instruments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    exchange: Mapped[str] = mapped_column(String(12), default="NSE")
    sector: Mapped[str] = mapped_column(String(64), default="UNKNOWN")
    eligible: Mapped[bool] = mapped_column(Boolean, default=True)


class MarketCandle(Base, Timed):
    __tablename__ = "market_candles"
    __table_args__ = (
        UniqueConstraint("instrument_id", "interval", "started_at"),
        CheckConstraint("high >= low AND volume >= 0"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), index=True)
    interval: Mapped[str] = mapped_column(String(8), default="1m")
    open: Mapped[Decimal] = mapped_column(MONEY)
    high: Mapped[Decimal] = mapped_column(MONEY)
    low: Mapped[Decimal] = mapped_column(MONEY)
    close: Mapped[Decimal] = mapped_column(MONEY)
    volume: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(32), default="simulated")


class MarketSnapshot(Base, Timed):
    __tablename__ = "market_snapshots"
    __table_args__ = (
        UniqueConstraint("instrument_id", "occurrence_key"),
        CheckConstraint("price > 0 AND volume >= 0"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), index=True)
    price: Mapped[Decimal] = mapped_column(MONEY)
    volume: Mapped[int] = mapped_column(Integer)
    exchange_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(32), default="simulated")
    scenario: Mapped[str] = mapped_column(String(32), default="TRENDING_UP")
    occurrence_key: Mapped[str] = mapped_column(String(160))


class IntelligenceTradingSession(Base):
    __tablename__ = "intelligence_trading_sessions"
    session_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    session_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    market_open: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    market_close: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_holiday: Mapped[bool] = mapped_column(Boolean, default=False)
    is_half_session: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IntelligenceProviderStatus(Base):
    __tablename__ = "intelligence_provider_status"
    provider: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_source_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    freshness_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="unknown")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IntelligenceInstrument(Base, Timed):
    __tablename__ = "intelligence_instruments"
    __table_args__ = (UniqueConstraint("exchange", "symbol", "valid_from"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    exchange: Mapped[str] = mapped_column(String(32), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    exchange_token: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    instrument_type: Mapped[str] = mapped_column(String(32), default="equity")
    sector: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_version: Mapped[int] = mapped_column(Integer, default=1)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class IntelligenceCandle(Base):
    __tablename__ = "intelligence_candles"
    __table_args__ = (
        CheckConstraint("ended_at > started_at"),
        CheckConstraint("open_price > 0 AND high_price > 0 AND low_price > 0 AND close_price > 0"),
        CheckConstraint(
            "high_price >= low_price AND high_price >= open_price AND high_price >= close_price"
        ),
        CheckConstraint("low_price <= open_price AND low_price <= close_price"),
        CheckConstraint("volume >= 0 AND trade_count >= 0"),
        UniqueConstraint("instrument_id", "interval", "started_at", "source", "revision"),
        Index("ix_intelligence_candles_lookup", "instrument_id", "interval", "started_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    instrument_id: Mapped[str] = mapped_column(
        ForeignKey("intelligence_instruments.id"), index=True
    )
    interval: Mapped[str] = mapped_column(String(8), index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    open_price: Mapped[Decimal] = mapped_column(MONEY)
    high_price: Mapped[Decimal] = mapped_column(MONEY)
    low_price: Mapped[Decimal] = mapped_column(MONEY)
    close_price: Mapped[Decimal] = mapped_column(MONEY)
    volume: Mapped[int] = mapped_column(Integer)
    trade_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    freshness_seconds: Mapped[int] = mapped_column(Integer)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    is_authoritative: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    supersedes_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(20), default="valid", index=True)
    validation_errors: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IntelligenceCandleRejection(Base):
    __tablename__ = "intelligence_candle_rejections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    instrument_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    interval: Mapped[str] = mapped_column(String(8))
    source: Mapped[str] = mapped_column(String(64))
    source_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    error_codes: Mapped[list] = mapped_column(JSON, default=list)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FeatureValue(Base):
    __tablename__ = "feature_values"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id", "interval", "observed_at", "feature_name", "feature_version"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    instrument_id: Mapped[str] = mapped_column(String(36), index=True)
    interval: Mapped[str] = mapped_column(String(8), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    feature_name: Mapped[str] = mapped_column(String(64), index=True)
    feature_version: Mapped[str] = mapped_column(String(16))
    value: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    calculation_version: Mapped[str] = mapped_column(String(32), default="1")
    source_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lineage: Mapped[dict] = mapped_column(JSON, default=dict)


class EvidenceEvaluation(Base):
    __tablename__ = "evidence_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id", "interval", "evaluation_time", "evidence_code", "rule_version"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    instrument_id: Mapped[str] = mapped_column(String(36), index=True)
    interval: Mapped[str] = mapped_column(String(8), index=True)
    evaluation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    evidence_code: Mapped[str] = mapped_column(String(64), index=True)
    rule_version: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(32))
    direction: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(32))
    strength: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    readiness: Mapped[str] = mapped_column(String(16))
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    lineage: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExternalRawItem(Base):
    __tablename__ = "external_raw_items"
    __table_args__ = (UniqueConstraint("provider", "provider_item_id", "payload_checksum"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    provider_item_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload_checksum: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[dict] = mapped_column(JSON)
    processing_status: Mapped[str] = mapped_column(String(24), default="received")


class ExternalItem(Base):
    __tablename__ = "external_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    canonical_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(512))
    normalized_title: Mapped[str] = mapped_column(String(512))
    canonical_url: Mapped[str] = mapped_column(String(2048))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    processing_version: Mapped[str] = mapped_column(String(16), default="1")
    raw_item_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExternalDuplicateLink(Base):
    __tablename__ = "external_duplicate_links"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    canonical_item_id: Mapped[str] = mapped_column(String(36), index=True)
    duplicate_item_id: Mapped[str] = mapped_column(String(36), index=True)
    relationship_type: Mapped[str] = mapped_column(String(32))
    similarity_score: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    rule_version: Mapped[str] = mapped_column(String(16))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExternalEntityAlias(Base):
    __tablename__ = "external_entity_aliases"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "normalized_alias", "valid_from"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    alias: Mapped[str] = mapped_column(String(256))
    normalized_alias: Mapped[str] = mapped_column(String(256), index=True)
    alias_type: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(64))
    priority: Mapped[int] = mapped_column(Integer, default=1)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ExternalEntityMapping(Base):
    __tablename__ = "external_entity_mappings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    external_item_id: Mapped[str] = mapped_column(String(36), index=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    relationship_type: Mapped[str] = mapped_column(String(32))
    mapping_method: Mapped[str] = mapped_column(String(32))
    mapping_score: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    matched_text: Mapped[str] = mapped_column(String(256))
    alias_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    rule_version: Mapped[str] = mapped_column(String(16), default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExternalClassification(Base):
    __tablename__ = "external_classifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    external_item_id: Mapped[str] = mapped_column(String(36), index=True)
    category_code: Mapped[str] = mapped_column(String(64), index=True)
    category_version: Mapped[str] = mapped_column(String(16))
    impact: Mapped[str] = mapped_column(String(16))
    confirmation: Mapped[str] = mapped_column(String(16))
    rule_strength: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    matched_phrases: Mapped[list] = mapped_column(JSON, default=list)
    excluded_phrases: Mapped[list] = mapped_column(JSON, default=list)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    importance_level: Mapped[str] = mapped_column(String(16), default="low")
    importance_signals: Mapped[dict] = mapped_column(JSON, default=dict)


class ExternalIntelligenceReadiness(Base):
    __tablename__ = "external_intelligence_readiness"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    provider: Mapped[str] = mapped_column(String(32), index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    blocking_reasons: Mapped[list] = mapped_column(JSON, default=list)
    warning_reasons: Mapped[list] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExternalItemRelation(Base):
    __tablename__ = "external_item_relations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    source_item_id: Mapped[str] = mapped_column(String(36), index=True)
    target_item_id: Mapped[str] = mapped_column(String(36), index=True)
    relation_type: Mapped[str] = mapped_column(String(32))
    rule_version: Mapped[str] = mapped_column(String(16))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class JsonRecord(Base, Timed):
    __abstract__ = True
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class FeatureSnapshot(JsonRecord):
    __tablename__ = "feature_snapshots"
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), index=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    version: Mapped[str] = mapped_column(String(32))


class MarketRegime(JsonRecord):
    __tablename__ = "market_regimes"
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), index=True)
    regime: Mapped[str] = mapped_column(String(40))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StrategyRegistry(JsonRecord):
    __tablename__ = "strategy_registry"
    name: Mapped[str] = mapped_column(String(80), unique=True)


class StrategyVersion(JsonRecord):
    __tablename__ = "strategy_versions"
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategy_registry.id"))
    version: Mapped[str] = mapped_column(String(32))
    __table_args__ = (UniqueConstraint("strategy_id", "version"),)


class StrategySignal(JsonRecord):
    __tablename__ = "strategy_signals"
    strategy_version_id: Mapped[str] = mapped_column(ForeignKey("strategy_versions.id"))
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"))


class TradeCandidate(JsonRecord):
    __tablename__ = "trade_candidates"
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"))
    strategy_version_id: Mapped[str] = mapped_column(ForeignKey("strategy_versions.id"))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TradeDecision(JsonRecord):
    __tablename__ = "trade_decisions"
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), index=True)
    candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("trade_candidates.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(12), index=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DecisionEvidence(JsonRecord):
    __tablename__ = "decision_evidence"
    decision_id: Mapped[str] = mapped_column(ForeignKey("trade_decisions.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(40))


class RiskEvaluation(JsonRecord):
    __tablename__ = "risk_evaluations"
    decision_id: Mapped[str] = mapped_column(ForeignKey("trade_decisions.id"), index=True)
    approved: Mapped[bool] = mapped_column(Boolean)
    position_size: Mapped[Decimal] = mapped_column(QTY)
    monetary_risk: Mapped[Decimal] = mapped_column(MONEY)


class RiskRuleResult(Base):
    __tablename__ = "risk_rule_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    risk_evaluation_id: Mapped[str] = mapped_column(ForeignKey("risk_evaluations.id"), index=True)
    configuration_version: Mapped[int] = mapped_column(Integer, default=1)
    rule_name: Mapped[str] = mapped_column(String(80), index=True)
    rule_version: Mapped[str] = mapped_column(String(20), default="1.0")
    threshold: Mapped[str] = mapped_column(String(80))
    observed: Mapped[str] = mapped_column(String(80))
    unit: Mapped[str] = mapped_column(String(20), default="")
    passed: Mapped[bool] = mapped_column(Boolean)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    reason_code: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(String(240))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ApprovalRequest(JsonRecord):
    __tablename__ = "approval_requests"
    decision_id: Mapped[str] = mapped_column(ForeignKey("trade_decisions.id"), unique=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class Order(JsonRecord):
    __tablename__ = "orders"
    # BUY orders are linked to a manual approval; SELL exits are independently authorised.
    approval_id: Mapped[str | None] = mapped_column(
        ForeignKey("approval_requests.id"), unique=True, nullable=True
    )
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), index=True)
    side: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(24), index=True)
    quantity: Mapped[Decimal] = mapped_column(QTY)
    filled_quantity: Mapped[Decimal] = mapped_column(QTY, default=0)
    average_price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    charges: Mapped[Decimal] = mapped_column(MONEY, default=0)
    idempotency_key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))


class OrderEvent(JsonRecord):
    __tablename__ = "order_events"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    external_event_id: Mapped[str] = mapped_column(String(80), unique=True)


class Trade(JsonRecord):
    __tablename__ = "trades"
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"))
    event_id: Mapped[str] = mapped_column(String(80), unique=True)
    side: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[Decimal] = mapped_column(QTY)
    price: Mapped[Decimal] = mapped_column(MONEY)
    charges: Mapped[Decimal] = mapped_column(MONEY)
    realised_pnl: Mapped[Decimal] = mapped_column(MONEY, default=0)


class Position(JsonRecord):
    __tablename__ = "positions"
    __table_args__ = (CheckConstraint("quantity >= 0"),)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), unique=True)
    quantity: Mapped[Decimal] = mapped_column(QTY)
    average_price: Mapped[Decimal] = mapped_column(MONEY)
    current_price: Mapped[Decimal] = mapped_column(MONEY)
    realised_pnl: Mapped[Decimal] = mapped_column(MONEY, default=0)
    charges: Mapped[Decimal] = mapped_column(MONEY, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)


class PortfolioSnapshot(JsonRecord):
    __tablename__ = "portfolio_snapshots"
    cash: Mapped[Decimal] = mapped_column(MONEY)
    market_value: Mapped[Decimal] = mapped_column(MONEY)
    portfolio_value: Mapped[Decimal] = mapped_column(MONEY)


class CashLedger(JsonRecord):
    __tablename__ = "cash_ledger"
    entry_type: Mapped[str] = mapped_column(String(32), index=True)
    amount: Mapped[Decimal] = mapped_column(MONEY)
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(80))
    event_id: Mapped[str] = mapped_column(String(80), unique=True)


class TradeReview(JsonRecord):
    __tablename__ = "trade_reviews"
    trade_id: Mapped[str] = mapped_column(ForeignKey("trades.id"), unique=True)


class Alert(Base, Timed):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("issue_key", "status"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    alert_type: Mapped[str] = mapped_column(String(64), index=True)
    issue_key: Mapped[str] = mapped_column(String(160), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    reason_code: Mapped[str] = mapped_column(String(80))
    instrument_id: Mapped[str | None] = mapped_column(ForeignKey("instruments.id"), nullable=True)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(80))
    actor: Mapped[str] = mapped_column(String(80))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    correlation_id: Mapped[str] = mapped_column(String(80), index=True)
    causation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class SystemSetting(Base, Timed):
    __tablename__ = "system_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class JobRun(JsonRecord):
    __tablename__ = "job_runs"
    job_key: Mapped[str] = mapped_column(String(120), unique=True)
    job_name: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)


class ScheduledJob(Base, Timed):
    """Durable scheduler definition; worker leases are stored in PostgreSQL."""

    __tablename__ = "scheduled_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    job_type: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="idle", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    lock_owner: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lock_acquired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class OpportunityRecord(Base):
    """Auditable research-priority result; never an order or recommendation."""

    __tablename__ = "opportunity_records"
    __table_args__ = (UniqueConstraint("instrument_id", "evaluated_at", "rule_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    instrument_id: Mapped[str] = mapped_column(String(36), index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    orientation: Mapped[str] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(32), index=True)
    score: Mapped[int] = mapped_column(Integer)
    rule_version: Mapped[str] = mapped_column(String(32))
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    cautions: Mapped[list] = mapped_column(JSON, default=list)
    contributions: Mapped[list] = mapped_column(JSON, default=list)
    lineage: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class OpportunityRule(Base):
    __tablename__ = "opportunity_rules"
    __table_args__ = (UniqueConstraint("rule_code", "rule_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    rule_code: Mapped[str] = mapped_column(String(80), index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(64))
    rule_version: Mapped[str] = mapped_column(String(32))
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class OpportunityDiscoveryRun(Base):
    __tablename__ = "opportunity_discovery_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    rule_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), index=True)
    instrument_count: Mapped[int] = mapped_column(Integer, default=0)
    opportunity_count: Mapped[int] = mapped_column(Integer, default=0)
    lineage: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ResearchSnapshot(Base):
    __tablename__ = "research_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    snapshot_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    instrument_id: Mapped[str] = mapped_column(String(36), index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    schema_version: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    lineage: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class MLDataset(Base):
    __tablename__ = "ml_datasets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    dataset_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    dataset_code: Mapped[str] = mapped_column(String(80), index=True)
    dataset_version: Mapped[str] = mapped_column(String(32))
    schema_version: Mapped[str] = mapped_column(String(32))
    row_count: Mapped[int] = mapped_column(Integer)
    manifest: Mapped[dict] = mapped_column(JSON)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class MLLabelRecord(Base):
    __tablename__ = "ml_label_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    row_identity: Mapped[str] = mapped_column(String(64), index=True)
    outcome_code: Mapped[str] = mapped_column(String(80))
    outcome_version: Mapped[str] = mapped_column(String(32))
    label_code: Mapped[str] = mapped_column(String(80))
    label_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), index=True)
    feature_cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    lineage: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class MLTrainingRun(Base):
    __tablename__ = "ml_training_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    training_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    dataset_identity: Mapped[str] = mapped_column(String(64), index=True)
    label_spec: Mapped[str] = mapped_column(String(100))
    algorithm: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24))
    metrics: Mapped[dict] = mapped_column(JSON)
    lineage: Mapped[dict] = mapped_column(JSON)
    research_only: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class MetricAggregationReport(Base):
    __tablename__ = "metric_aggregation_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    report_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    validation_id: Mapped[str] = mapped_column(String(64), index=True)
    fold_count: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    lineage: Mapped[dict] = mapped_column(JSON)
    research_only: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RobustnessReport(Base):
    __tablename__ = "robustness_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    summary_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    validation_id: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    lineage: Mapped[dict] = mapped_column(JSON)
    historical_only: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ValidationDecisionRecord(Base):
    __tablename__ = "validation_decision_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    decision_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    validation_id: Mapped[str] = mapped_column(String(64), index=True)
    policy_code: Mapped[str] = mapped_column(String(80))
    policy_version: Mapped[str] = mapped_column(String(32))
    decision: Mapped[str] = mapped_column(String(24), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    lineage: Mapped[dict] = mapped_column(JSON)
    research_only: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ModelRegistryDefinition(Base):
    __tablename__ = "model_registry_definitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    definition_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    definition_code: Mapped[str] = mapped_column(String(80), index=True)
    definition_version: Mapped[str] = mapped_column(String(32))
    definition_type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ModelVersionRecord(Base):
    __tablename__ = "model_version_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    version_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    namespace: Mapped[str] = mapped_column(String(80), index=True)
    model_code: Mapped[str] = mapped_column(String(80), index=True)
    semantic_version: Mapped[str] = mapped_column(String(32))
    package_identity: Mapped[str] = mapped_column(String(64))
    predecessor_identity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ModelCandidateRecord(Base):
    __tablename__ = "model_candidate_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    candidate_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    version_identity: Mapped[str] = mapped_column(String(64), index=True)
    registration_identity: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="registered")
    payload: Mapped[dict] = mapped_column(JSON)
    lineage: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PromotionRequestRecord(Base):
    __tablename__ = "promotion_request_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    candidate_identity: Mapped[str] = mapped_column(String(64), index=True)
    stage: Mapped[str] = mapped_column(String(40))
    decision: Mapped[str] = mapped_column(String(32), default="needs_review")
    payload: Mapped[dict] = mapped_column(JSON)
    lineage: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ModelRoleAssignment(Base):
    __tablename__ = "model_role_assignments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    assignment_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    scope: Mapped[str] = mapped_column(String(80), index=True)
    champion_identity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    challenger_identities: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default="active")
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RegistryAuditReport(Base):
    __tablename__ = "registry_audit_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    report_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    scope: Mapped[str] = mapped_column(String(80), index=True)
    replayable: Mapped[bool] = mapped_column(Boolean)
    payload: Mapped[dict] = mapped_column(JSON)
    findings: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ModelLoadManifest(Base):
    __tablename__ = "model_load_manifests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    load_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    version_identity: Mapped[str] = mapped_column(String(64), index=True)
    handle_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class OfflinePredictionRecord(Base):
    __tablename__ = "offline_prediction_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    prediction_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    model_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24))
    payload: Mapped[dict] = mapped_column(JSON)
    lineage: Mapped[dict] = mapped_column(JSON)
    offline_only: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionValidationPolicy(Base):
    __tablename__ = "ml_prediction_validation_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    validation_policy_code: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[str] = mapped_column(String(24))
    description: Mapped[str] = mapped_column(String(300))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_prediction_statuses: Mapped[list] = mapped_column(JSON)
    required_prediction_policy: Mapped[dict] = mapped_column(JSON)
    required_output_contract: Mapped[dict] = mapped_column(JSON)
    required_model_status: Mapped[str] = mapped_column(String(40))
    required_manifest_version: Mapped[str] = mapped_column(String(40))
    validation_mode: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionValidationRequest(Base):
    __tablename__ = "ml_prediction_validation_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    prediction_result_identity: Mapped[str] = mapped_column(String(64), index=True)
    validation_policy: Mapped[str] = mapped_column(String(100))
    requested_by: Mapped[str] = mapped_column(String(120))
    request_reason: Mapped[str] = mapped_column(String(300))
    request_status: Mapped[str] = mapped_column(String(24), default="requested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionValidationRule(Base):
    __tablename__ = "ml_prediction_validation_rules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    rule_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(300))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionValidationResult(Base):
    __tablename__ = "ml_prediction_validation_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    decision: Mapped[str] = mapped_column(String(32))
    eligibility: Mapped[str] = mapped_column(String(32))
    rule_outcomes: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionValidationManifest(Base):
    __tablename__ = "ml_prediction_validation_manifests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    manifest_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_identity: Mapped[str] = mapped_column(String(64), index=True)
    prediction_identity: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    manifest_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionValidationEvent(Base):
    __tablename__ = "ml_prediction_validation_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_identity: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class StatisticalValidationPolicy(Base):
    __tablename__ = "ml_statistical_validation_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(24))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class StatisticalValidationRequest(Base):
    __tablename__ = "ml_statistical_validation_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    parent_validation_request_identity: Mapped[str] = mapped_column(String(64), index=True)
    prediction_result_identity: Mapped[str] = mapped_column(String(64), index=True)
    policy_code: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(32), default="requested")
    request_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ConfidenceEvidence(Base):
    __tablename__ = "ml_confidence_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evidence_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    prediction_result_identity: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    evidence_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class StatisticalValidationResult(Base):
    __tablename__ = "ml_statistical_validation_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    request_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    decision: Mapped[str] = mapped_column(String(32))
    rule_results: Mapped[list] = mapped_column(JSON)
    result_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class StatisticalValidationManifest(Base):
    __tablename__ = "ml_statistical_validation_manifests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    manifest_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_identity: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    manifest_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class StatisticalValidationEvent(Base):
    __tablename__ = "ml_statistical_validation_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_identity: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(48))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class StatisticalValidationLifecycle(Base):
    __tablename__ = "ml_statistical_validation_lifecycle"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lifecycle_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_identity: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(String(300))
    actor_identity: Mapped[str] = mapped_column(String(120))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class CalibrationEvidence(Base):
    __tablename__ = "ml_calibration_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evidence_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    model_version_identity: Mapped[str] = mapped_column(String(64), index=True)
    output_contract_identity: Mapped[str] = mapped_column(String(64))
    validation_dataset_identity: Mapped[str] = mapped_column(String(64))
    task_type: Mapped[str] = mapped_column(String(32))
    sample_count: Mapped[int] = mapped_column(Integer)
    expected_calibration_error: Mapped[float] = mapped_column(Float)
    maximum_calibration_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    brier_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    log_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    evidence_checksum: Mapped[str] = mapped_column(String(64))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)


class PredictionSafetyPolicy(Base):
    __tablename__ = "ml_prediction_safety_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(24))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionSafetyResult(Base):
    __tablename__ = "ml_prediction_safety_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    safety_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    prediction_identity: Mapped[str] = mapped_column(String(64), index=True)
    decision: Mapped[str] = mapped_column(String(32))
    rule_results: Mapped[list] = mapped_column(JSON)
    result_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionSafetyManifest(Base):
    __tablename__ = "ml_prediction_safety_manifests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    manifest_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    safety_identity: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    manifest_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionSafetyEvent(Base):
    __tablename__ = "ml_prediction_safety_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    safety_identity: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(48))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionSafetyEvidence(Base):
    __tablename__ = "ml_prediction_safety_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evidence_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    safety_identity: Mapped[str] = mapped_column(String(64), index=True)
    evidence_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    evidence_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionGovernancePolicy(Base):
    __tablename__ = "ml_prediction_governance_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(24))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionGovernanceDecision(Base):
    __tablename__ = "ml_prediction_governance_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    governance_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    prediction_identity: Mapped[str] = mapped_column(String(64), index=True)
    decision: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    decision_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionGovernanceManifest(Base):
    __tablename__ = "ml_prediction_governance_manifests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    manifest_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    governance_identity: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    manifest_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionGovernanceEvent(Base):
    __tablename__ = "ml_prediction_governance_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    governance_identity: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(48))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BatchPredictionPolicy(Base):
    __tablename__ = "ml_batch_prediction_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(24))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BatchPredictionRequest(Base):
    __tablename__ = "ml_batch_prediction_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    batch_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    requested_by: Mapped[str] = mapped_column(String(128))
    policy_code: Mapped[str] = mapped_column(String(100))
    universe_type: Mapped[str] = mapped_column(String(48))
    universe: Mapped[dict] = mapped_column(JSON)
    as_of_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="created")
    request_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BatchPredictionItem(Base):
    __tablename__ = "ml_batch_prediction_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    item_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BatchPredictionEvent(Base):
    __tablename__ = "ml_batch_prediction_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    event_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(48))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BatchPredictionManifest(Base):
    __tablename__ = "ml_batch_prediction_manifests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    batch_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BatchPredictionPartition(Base):
    __tablename__ = "ml_batch_prediction_partitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partition_number: Mapped[int] = mapped_column(Integer)
    first_ordinal: Mapped[int] = mapped_column(Integer)
    last_ordinal: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="planned")
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BatchPredictionAttempt(Base):
    __tablename__ = "ml_batch_prediction_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    item_key: Mapped[str] = mapped_column(String(128), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(48))
    outcome: Mapped[str] = mapped_column(String(32))
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean, default=False)
    attempt_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BatchPredictionCheckpoint(Base):
    __tablename__ = "ml_batch_prediction_checkpoints"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    item_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checkpoint_type: Mapped[str] = mapped_column(String(64))
    sequence: Mapped[int] = mapped_column(Integer)
    state_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BatchPredictionCancellation(Base):
    __tablename__ = "ml_batch_prediction_cancellations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    batch_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    requested_by: Mapped[str] = mapped_column(String(128))
    reason: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(24), default="requested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BatchPredictionWorkerLease(Base):
    __tablename__ = "ml_batch_prediction_worker_leases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    partition_id: Mapped[str] = mapped_column(String(36), index=True)
    worker_key: Mapped[str] = mapped_column(String(128))
    lease_token_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="active")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BatchPredictionReplay(Base):
    __tablename__ = "ml_batch_prediction_replays"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    source_batch_id: Mapped[str] = mapped_column(String(64), index=True)
    replay_batch_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    mode: Mapped[str] = mapped_column(String(32))
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ExplainabilityPolicy(Base):
    __tablename__ = "ml_prediction_explainability_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True)
    version: Mapped[str] = mapped_column(String(24))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ExplainabilityRequest(Base):
    __tablename__ = "ml_prediction_explainability_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    explainability_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    prediction_identity: Mapped[str] = mapped_column(String(64), index=True)
    requested_by: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(24), default="requested")
    eligibility: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ExplainabilityProvenance(Base):
    __tablename__ = "ml_prediction_provenance"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    explainability_id: Mapped[str] = mapped_column(String(64), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ExplainabilityManifest(Base):
    __tablename__ = "ml_prediction_explainability_manifests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    explainability_id: Mapped[str] = mapped_column(String(64), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ExplainabilityEvent(Base):
    __tablename__ = "ml_prediction_explainability_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    explainability_id: Mapped[str] = mapped_column(String(64), index=True)
    event_identity: Mapped[str] = mapped_column(String(64), unique=True)
    event_type: Mapped[str] = mapped_column(String(48))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ExplainabilityLineageRecord(Base):
    __tablename__ = "ml_prediction_explainability_lineage"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    record_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    record_type: Mapped[str] = mapped_column(String(24))
    source_identity: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AttributionPolicy(Base):
    __tablename__ = "ml_prediction_attribution_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    algorithm_priority: Mapped[dict] = mapped_column(JSON)
    normalize_scores: Mapped[bool] = mapped_column(Boolean, default=True)
    precision_digits: Mapped[int] = mapped_column(Integer, default=8)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AttributionAlgorithm(Base):
    __tablename__ = "ml_prediction_attribution_algorithms"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    algorithm: Mapped[str] = mapped_column(String(80), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class LocalExplanation(Base):
    __tablename__ = "ml_prediction_local_explanations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    explanation_identity: Mapped[str] = mapped_column(String(64), unique=True)
    explainability_id: Mapped[str] = mapped_column(String(64))
    prediction_identity: Mapped[str] = mapped_column(String(64))
    algorithm: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class LocalAttribution(Base):
    __tablename__ = "ml_prediction_local_attributions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    explanation_identity: Mapped[str] = mapped_column(String(64), index=True)
    feature_name: Mapped[str] = mapped_column(String(128))
    feature_index: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class GlobalExplainabilityPolicy(Base):
    __tablename__ = "ml_prediction_global_explainability_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    minimum_sample_size: Mapped[int] = mapped_column(Integer, default=1)
    aggregation_strategy: Mapped[str] = mapped_column(String(32), default="mean_absolute")
    top_feature_limit: Mapped[int] = mapped_column(Integer, default=20)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class GlobalExplanation(Base):
    __tablename__ = "ml_prediction_global_explanations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    explanation_identity: Mapped[str] = mapped_column(String(64), unique=True)
    dataset_identity: Mapped[str] = mapped_column(String(64))
    model_identity: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class GlobalImportance(Base):
    __tablename__ = "ml_prediction_global_feature_importance"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    explanation_identity: Mapped[str] = mapped_column(String(64), index=True)
    feature_name: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class GlobalStability(Base):
    __tablename__ = "ml_prediction_global_stability"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    explanation_identity: Mapped[str] = mapped_column(String(64), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ExplainabilityGovernance(Base):
    __tablename__ = "ml_explainability_governance"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    artifact_id: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ExplainabilityGovernanceRecord(Base):
    __tablename__ = "ml_explainability_governance_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    artifact_id: Mapped[str] = mapped_column(String(64), index=True)
    record_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RuntimeOperationPolicy(Base):
    __tablename__ = "ml_runtime_operation_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RuntimeHealthSnapshot(Base):
    __tablename__ = "ml_runtime_health_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    snapshot_checksum: Mapped[str] = mapped_column(String(64), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RuntimeService(Base):
    __tablename__ = "ml_runtime_services"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    service_name: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RuntimeIncident(Base):
    __tablename__ = "ml_runtime_incidents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    incident_id: Mapped[str] = mapped_column(String(64), unique=True)
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(24))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RuntimeReport(Base):
    __tablename__ = "ml_runtime_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    report_checksum: Mapped[str] = mapped_column(String(64), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RuntimeOperationalRecord(Base):
    __tablename__ = "ml_runtime_operational_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    record_identity: Mapped[str] = mapped_column(String(64), unique=True)
    record_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class EvaluationPolicy(Base):
    __tablename__ = "ml_evaluation_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class EvaluationRequest(Base):
    __tablename__ = "ml_evaluation_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evaluation_id: Mapped[str] = mapped_column(String(64), unique=True)
    dataset_id: Mapped[str] = mapped_column(String(64))
    model_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="requested")
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class EvaluationRecord(Base):
    __tablename__ = "ml_evaluation_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evaluation_id: Mapped[str] = mapped_column(String(64), index=True)
    record_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class MetricPolicy(Base):
    __tablename__ = "ml_metric_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class MetricResult(Base):
    __tablename__ = "ml_metric_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evaluation_id: Mapped[str] = mapped_column(String(64), index=True)
    metric: Mapped[str] = mapped_column(String(48))
    family: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    result_checksum: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class CalibrationPolicy(Base):
    __tablename__ = "ml_calibration_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    minimum_samples: Mapped[int] = mapped_column(Integer, default=1)
    maximum_bins: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class CalibrationReliability(Base):
    __tablename__ = "ml_reliability_objects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evaluation_id: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    reliability_checksum: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BenchmarkPolicy(Base):
    __tablename__ = "ml_benchmark_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BenchmarkComparison(Base):
    __tablename__ = "ml_benchmark_comparisons"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    benchmark_id: Mapped[str] = mapped_column(String(64), unique=True)
    left_model: Mapped[str] = mapped_column(String(64))
    right_model: Mapped[str] = mapped_column(String(64))
    dataset_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RegimeEvaluationPolicy(Base):
    __tablename__ = "ml_regime_evaluation_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    minimum_samples: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RegimeEvaluation(Base):
    __tablename__ = "ml_regime_evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evaluation_identity: Mapped[str] = mapped_column(String(64), unique=True)
    source_evaluation_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PromotionReadinessPolicy(Base):
    __tablename__ = "ml_promotion_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_code: Mapped[str] = mapped_column(String(100), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PromotionReadiness(Base):
    __tablename__ = "ml_promotion_readiness"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    readiness_id: Mapped[str] = mapped_column(String(64), unique=True)
    model_id: Mapped[str] = mapped_column(String(64))
    dataset_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RegressionEvidence(Base):
    __tablename__ = "ml_regression_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evidence_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    prediction_result_identity: Mapped[str] = mapped_column(String(64), index=True)
    model_version_identity: Mapped[str] = mapped_column(String(64), index=True)
    validation_dataset_identity: Mapped[str] = mapped_column(String(64))
    predicted_value: Mapped[float] = mapped_column(Float)
    residual: Mapped[float | None] = mapped_column(Float, nullable=True)
    interval_lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    interval_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    uncertainty_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    evidence_checksum: Mapped[str] = mapped_column(String(64))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReferenceDistributionEvidence(Base):
    __tablename__ = "ml_reference_distribution_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    evidence_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    model_version_identity: Mapped[str] = mapped_column(String(64), index=True)
    output_contract_identity: Mapped[str] = mapped_column(String(64))
    validation_dataset_identity: Mapped[str] = mapped_column(String(64))
    task_type: Mapped[str] = mapped_column(String(32))
    lower_bound: Mapped[float] = mapped_column(Float)
    upper_bound: Mapped[float] = mapped_column(Float)
    tolerance: Mapped[float] = mapped_column(Float, default=0.0)
    sample_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSON)
    evidence_checksum: Mapped[str] = mapped_column(String(64))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StatisticalValidationReplay(Base):
    """Immutable persisted result of replaying a validation manifest."""

    __tablename__ = "ml_statistical_validation_replays"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    replay_identity: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_identity: Mapped[str] = mapped_column(String(64), index=True)
    manifest_identity: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(24))
    mismatches: Mapped[list] = mapped_column(JSON)
    replay_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


Index("ix_audit_entity", AuditLog.entity_type, AuditLog.entity_id)
