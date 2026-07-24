# Concurrency

Approval and position operations use `SELECT ... FOR UPDATE`; idempotency and external-event unique
constraints protect duplicate requests. Scheduler claims use PostgreSQL row locks. Redis is never
the correctness boundary for money or positions.
