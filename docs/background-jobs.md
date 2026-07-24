# Background jobs

The scheduler registry contains simulated price, candle, feature, regime, decision, expiry,
stop/target, EOD, snapshot, reconciliation, review, stale-data, health, and audit-retention job
types. The worker polls PostgreSQL every five seconds and records successful or failed runs. Manual
API execution invokes the same transactional service. Expiry, portfolio snapshot, reconciliation,
system health, and non-destructive retention-policy handlers are implemented; remaining market and
execution handlers are explicitly reported as skipped until their dedicated transactional services
are added.
