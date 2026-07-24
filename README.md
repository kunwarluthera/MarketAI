# Market AI

A local-first Indian cash-equity research, backtesting, and paper-trading terminal. It starts in
`PAPER` mode, has no live order execution, and requires explicit approval for every actionable
paper trade. It is decision support—not investment advice and not a promise of performance.

## Start locally

Requirements: Docker Desktop, Docker Compose, Python 3.11+ (3.12 recommended), and Node 20+.

```bash
make setup
make up
make migrate
make seed
```

Open http://localhost:5173 and sign in with `demo` / `papertrade`.
API: http://localhost:8000 · OpenAPI: http://localhost:8000/docs

For foreground development use `make dev`. The API, worker, and frontend are all started by
Compose. To run them separately after `make setup`:

```bash
.venv/bin/uvicorn app.main:app --app-dir apps/api --reload
python apps/worker/worker.py
cd apps/web && npm run dev
```

Verification and operations:

```bash
make test
make lint
make typecheck
make e2e
make health
make logs
make reset-demo
make down
```

Never place real credentials in `.env`. `LIVE_TRADING_ENABLED` is ignored by execution code in
this release: only the local `PaperBroker` flow exists.

## Working first slice

Seeded reproducible candles feed indicators, regime classification, VWAP Momentum candidates,
explicit decisions, risk sizing, approval requests, idempotent simulated fills, portfolio balances,
cash-ledger entries, and immutable audit events. The dashboard exposes command center, scanner,
decision desk, orders, portfolio, and operations views. A deterministic no-look-ahead demo
backtest endpoint is also available.

See [architecture](docs/architecture.md), [risk controls](docs/risk-controls.md), and the
[implementation plan](docs/implementation-plan.md).

Milestone 3 adds a PostgreSQL-backed scheduler registry with 15 durable job types, a restart-safe
worker, manual job execution, versioned risk configuration, EOD and ledger policy settings, and
operator documentation. The worker is observable through `/api/v1/system/jobs/status`; financial
state remains PostgreSQL-backed and paper-only.
