# Milestone 3 results

Implemented and verified: durable `scheduled_jobs`, 15 persisted job types, PostgreSQL worker
startup and polling, per-job transactional execution, manual job endpoint, scheduler status endpoint,
versioned risk configuration with required change reason, audit logging for configuration changes,
EOD/ledger policy configuration, and documented conservative same-candle handling.

Verified with Docker: migration `0004_scheduler`, Ruff clean, 4 PostgreSQL-backed API tests passing,
frontend production build previously passing, API readiness passing after restart, worker running,
and scheduler/risk endpoint smoke tests passing.

Additional completion work now includes persisted lease/heartbeat fields, structured handler
results, expiry/snapshot/reconciliation/retention handlers, normalized risk-rule results, and the
FastAPI lifespan migration. Remaining before the strict Milestone 3 completion criteria are actual
market/candle/feature/regime/decision and stop/target/EOD handlers, lease reclaim and retry-alert
services, daily-P&L/risk matrix, concurrency/rollback/restart suites, Playwright coverage, and the
Risk Settings UI.
