# Job recovery

A worker restart does not erase schedule definitions or financial state. Due jobs remain in
PostgreSQL and are claimed again. Failures are persisted with a safe message; no exception can
commit a partial financial transaction because the caller owns one SQLAlchemy transaction.
