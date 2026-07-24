# Milestone 2 plan: Durable Trading Core

## Current architecture and gaps

Milestone 1 used a deterministic market/strategy domain and a FastAPI process-local state object.
The durable refactor replaces authoritative state with SQLAlchemy repositories over PostgreSQL.
Redis remains reserved for queues, cache, fan-out, and short-lived locks. Pure calculations remain
in `app.domain`, `app.risk.domain`, and `app.portfolio.domain`; persistence/orchestration lives in
`app.paper_trading.service` and is split behind `common.models`, `common.db`, and `audit.service`.

## Persistence model

The `0002_durable_core` migration creates instruments, candles, feature snapshots, regimes, strategy
registry/versions/signals, candidates, decisions/evidence, risk evaluations, approvals, orders/order
events, trades, positions, portfolio snapshots, cash ledger, trade reviews, audit logs, system
settings, idempotency records, and job runs. Monetary and quantity columns are PostgreSQL NUMERIC;
every table has UTC timestamps and relevant foreign-key, unique, index, and check constraints.

## Transaction boundaries

API services use one SQLAlchemy session transaction for decision generation, approval/order/fill,
position exit, kill-switch updates, and reconciliation. Approval/order/fill/exit update their linked
records, ledger, snapshots, reviews, and audit events before commit; an exception rolls back all of
them. PostgreSQL uniqueness on idempotency and external event IDs makes replays safe.

## Restart recovery

Startup performs an idempotent seed only when the instrument table is empty. All reads reconstruct
state from PostgreSQL, so API and worker restarts preserve approvals, orders, fills, positions,
cash, snapshots, and audit records. A later worker pass will resume scheduled stop/target and EOD
jobs using `job_runs` keys.

## Test plan

Unit tests cover pure candles, indicators, regimes, weighted-average pricing, and P&L. API tests
cover PostgreSQL-backed approval, idempotency, exit, reconciliation, and audit persistence. The
next increment should add concurrent PostgreSQL sessions, rollback injection, Docker restart, and
browser smoke coverage.

## Migration notes

`0001_core` was the initial scaffold. `0002_durable_core` recreates the scaffold tables from the
complete SQLAlchemy metadata so existing local demo databases can be upgraded consistently. Do not
run downgrade against a database containing user paper history without a backup.
