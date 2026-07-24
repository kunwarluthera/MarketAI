from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
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


Index("ix_audit_entity", AuditLog.entity_type, AuditLog.entity_id)
