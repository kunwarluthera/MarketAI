# Persistence

PostgreSQL is the source of truth. `SessionLocal` opens short-lived request sessions and services
make financial changes in a single transaction. NUMERIC columns are converted to `Decimal`; JSON is
used only for explanatory evidence and safe metadata. Redis is not authoritative.
