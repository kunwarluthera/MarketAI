# Architecture

The system is a modular monolith with separate API, worker, and React processes. PostgreSQL is the
source of truth and Redis is non-authoritative infrastructure. Domain rules are
pure Python; delivery and provider adapters sit outside them. REST APIs are versioned under
`/api/v1`, while `/health`, `/readiness`, and `/docs` are operational endpoints.

The intended module boundaries are auth, instruments, market_data, data_quality, features,
market_regime, news, research, analysis_engines, strategies, models, backtesting, decisions, risk,
approvals, orders, paper_trading, portfolio, learning, alerts, scheduler, audit, broker_adapters,
news_adapters, llm, system_health, and settings. The first slice concentrates executable domain
logic in a compact module; subsequent milestones extract each boundary without changing its ports.

Target API families: system, instruments, market, scanner, research/news, strategies, models,
decisions, risk, approvals, paper trading, backtesting, learning, operations, and audit.
