# Milestone 3 plan: Durable background processing and risk governance

## Current gaps

Milestone 2 persisted trading state but the worker was a sleep-only process. Schedules, retries,
manual job controls, risk configuration versioning, and scheduler observability were incomplete.

## Architecture

`scheduled_jobs` is the durable schedule registry and `job_runs` records each attempt. A worker
claims due rows with PostgreSQL row locks and executes a bounded transactional service. Redis is
not a financial lock or source of truth. API manual-run endpoints use the same service as the
worker, so retries have one code path.

## Recovery and retries

Jobs are idempotent by durable keys and unique constraints. A failed run is marked failed with a
safe error payload and the schedule remains retryable. Worker restart simply scans due rows again;
committed financial transactions remain intact. The next increment adds explicit lease expiry and
exponential backoff fields to `job_runs`.

## Risk governance

`risk_config` is a versioned system setting containing all Milestone 3 thresholds, EOD policy,
reconciliation tolerance, kill switch, and averaging policy. Updates require a reason and append an
audit event. Decisions already persist their exact rule results; future work will normalize each
rule into a separate table and attach the config version to every evaluation.

## Test plan

Run PostgreSQL unit/API tests, scheduler manual-run tests, idempotent rerun tests, migration checks,
restart recovery, lint/type/build checks, and browser tests. Financial correctness remains gated by
the existing approval, paper-only, ledger, and reconciliation controls.

## Completion checklist

- [x] Durable scheduler registry and 15 job registrations
- [x] PostgreSQL lease and heartbeat fields
- [x] Structured handler results and typed job exceptions
- [x] Recommendation and approval expiry handlers
- [x] Portfolio snapshot, ledger reconciliation, health, and retention-policy handlers
- [x] Versioned risk configuration and normalized risk-rule table
- [x] API/manual job smoke tests and PostgreSQL critical-flow tests
- [ ] Durable simulated quote/candle/feature/regime/decision handlers
- [ ] Automatic stop/target/EOD handlers
- [ ] Lease reclaim, worker heartbeat, and retry-exhaustion alert service
- [ ] Full normalized daily-P&L/risk matrix
- [ ] PostgreSQL concurrency and rollback-injection suites
- [ ] Restart script, Playwright suite, and Risk Settings UI
