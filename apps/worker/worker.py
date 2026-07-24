"""Durable, low-memory PostgreSQL scheduler worker.

The database row lock is the correctness boundary. A crashed worker leaves a short lease that the
next pass can reclaim; every job service is expected to be idempotent and transactional.
"""
from __future__ import annotations

import os
import time
from datetime import UTC, timedelta
from sqlalchemy import select

from app.common.db import SessionLocal
from app.common.models import ScheduledJob
from app.scheduler.service import ensure_jobs, run_job, utcnow


WORKER_ID = os.getenv("HOSTNAME", "worker-local")


def tick() -> int:
    count = 0
    with SessionLocal.begin() as session:
        ensure_jobs(session)
        due = session.scalars(select(ScheduledJob).where(
            ScheduledJob.enabled.is_(True), ScheduledJob.next_run_at <= utcnow(),
            ScheduledJob.status.in_(["idle", "failed"])).order_by(ScheduledJob.next_run_at).limit(5)
        ).all()
    for job in due:
        # Each job has an independent transaction so one failure cannot poison the batch.
        try:
            with SessionLocal.begin() as session:
                run_job(session, job.job_type, WORKER_ID)
            count += 1
        except Exception as exc:  # noqa: BLE001 - persisted as failed job state
            print(f"job {job.job_type} failed: {type(exc).__name__}: {str(exc)[:160]}", flush=True)
    return count


if __name__ == "__main__":
    print(f"market-ai durable worker ready: {WORKER_ID}", flush=True)
    while True:
        try:
            tick()
        except Exception as exc:  # database interruptions are retried on the next loop
            print(f"scheduler connection failure: {type(exc).__name__}", flush=True)
        time.sleep(5)
