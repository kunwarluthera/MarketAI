# Implementation plan

## Architecture decisions

- Modular monolith: FastAPI owns domain orchestration; a small worker runs scheduled demo ticks. This keeps local memory use low while preserving boundaries.
- Ports and adapters: broker, news, and LLM providers are interfaces. Paper, mock-news, and deterministic-LLM implementations are defaults.
- Safety-first execution: strategies only emit candidates. Decisions pass data-quality and risk gates, then require an explicit approval before the paper broker accepts an idempotent order.
- Financial values use `Decimal` in Python and decimal strings over JSON.
- UTC is authoritative; the UI formats timestamps in `Asia/Kolkata`.
- Immutable domain events form the audit trail. PostgreSQL models and Alembic establish the durable persistence path; demo mode can run without external credentials.

## Milestones

1. Vertical slice: tick → candle → features → regime → VWAP candidate → decision → risk → approval → fill → portfolio → audit.
2. Local UI: login, command center, scanner, decisions, orders, portfolio, operations.
3. Persistence and background scheduling.
4. Remaining strategies and event-driven backtesting.
5. News, safe LLM explanations, model governance, and learning.
6. Read-only Dhan and Zerodha market-data adapters.

## Core entities

Instrument, Tick, Candle, FeatureSnapshot, MarketRegime, EvidenceResult, TradeCandidate,
TradeDecision, RiskEvaluation, ApprovalRequest, Order, Fill, Position, PortfolioSnapshot,
CashLedgerEntry, AuditLog, StrategyVersion, ModelVersion, BacktestRun, NewsArticle.

## API map

All application APIs live under `/api/v1`; health and readiness are public. Auth issues a local bearer token. Market simulation, decisions, approvals, paper orders, portfolio, audit, and backtests make up the first slice. The complete target map is documented in `docs/architecture.md`.

## Security controls

Single-user password hashing, bearer authentication, restricted CORS, rate-limiting middleware,
secret redaction, input validation, paper-only execution, kill switch, and no secret-bearing responses.

## Test plan

- Unit: candles, indicators, quality, regimes, strategies, risk, costs, idempotency, P&L.
- Integration: complete approved paper-trade lifecycle and rejected/stale paths.
- Frontend: rendering and API states.
- E2E: login, generate decision, approve, inspect portfolio and audit.

## Status

The first delivery implements the runnable safety-critical vertical slice and connected core UI.
Provider integrations, broad entity persistence, and advanced analytics remain incremental milestones.
