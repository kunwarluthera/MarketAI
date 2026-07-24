# Restart recovery

Start the stack, run migrations, and seed once. Restarting API or worker does not reseed or reset
trading data. API reads orders, positions, approvals, ledger, snapshots, and audits directly from
PostgreSQL. The durable worker image is safe to restart because job keys and transaction scopes are
designed for retries.
