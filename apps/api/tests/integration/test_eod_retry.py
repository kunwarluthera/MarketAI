from sqlalchemy import select, func
from datetime import datetime
from zoneinfo import ZoneInfo

from app.common.db import SessionLocal
from app.common.models import Alert, JobRun, Order, Position, Trade, ScheduledJob
from app.scheduler.eod_policy import EodExitPolicy, RetryableEodExitError
from app.scheduler.service import run_job, ensure_jobs
from tests.integration.test_automatic_stop_target import _scenario, _snapshot


class FailNTimesThenSucceed:
    def __init__(self, failures, delegate, target_id=None):
        self.remaining = failures
        self.calls = 0
        self.delegate = delegate
        self.target_id = target_id

    def __call__(self, session, position_id, quantity, reason, correlation):
        if self.target_id and position_id != self.target_id:
            return self.delegate(session, position_id, quantity, reason, correlation)
        self.calls += 1
        if self.remaining:
            self.remaining -= 1
            raise RetryableEodExitError("injected retryable failure")
        return self.delegate(session, position_id, quantity, reason, correlation)


class AlwaysFail:
    def __init__(self, target_id=None):
        self.calls = 0
        self.target_id = target_id

    def __call__(self, session, position_id, quantity, reason, correlation):
        if self.target_id and position_id != self.target_id:
            from app.paper_trading.service import exit_position

            return exit_position(session, position_id, quantity, reason, correlation)
        self.calls += 1
        raise RetryableEodExitError("sanitized injected failure")


class HookFail:
    def __init__(self, target_id, stage):
        self.target_id, self.stage, self.calls = target_id, stage, 0

    def __call__(self, session, position_id, quantity, reason, correlation):
        from app.paper_trading.service import exit_position

        if position_id != self.target_id:
            return exit_position(session, position_id, quantity, reason, correlation)
        self.calls += 1

        def hook(stage):
            if stage == self.stage:
                raise RetryableEodExitError("post-write injected failure")

        return exit_position(session, position_id, quantity, reason, correlation, failure_hook=hook)


def _run(session, executor, policy=None):
    job = session.scalar(select(ScheduledJob).where(ScheduledJob.job_type == "EOD_POSITION_EXIT"))
    if job is None:
        ensure_jobs(session)
        job = session.scalar(
            select(ScheduledJob).where(ScheduledJob.job_type == "EOD_POSITION_EXIT")
        )
    job.payload = {**(job.payload or {}), "force": True}
    return run_job(
        session,
        "EOD_POSITION_EXIT",
        evaluation_time=datetime(2026, 7, 20, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
        eod_policy=policy or EodExitPolicy(cutoff_time=datetime.strptime("09:00", "%H:%M").time()),
        exit_executor=executor,
    )


def test_eod_retry_succeeds_before_exhaustion_without_failure_alert():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _snapshot(s, i, "102")
        from app.paper_trading.service import exit_position

        executor = FailNTimesThenSucceed(2, exit_position, p.id)
        _run(s, executor)
        assert executor.calls == 3
        assert s.scalar(select(Position).where(Position.id == p.id)).quantity == 0
        assert (
            s.scalar(
                select(Alert).where(
                    Alert.instrument_id == i.id,
                    Alert.alert_type == "EOD_EXIT_FAILED",
                    Alert.status == "open",
                )
            )
            is None
        )


def test_eod_retry_exhaustion_creates_failure_alert():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _snapshot(s, i, "102")
        executor = AlwaysFail(p.id)
        _run(s, executor)
        alert = s.scalar(
            select(Alert).where(
                Alert.instrument_id == i.id,
                Alert.alert_type == "EOD_EXIT_FAILED",
                Alert.status == "open",
            )
        )
        assert executor.calls == 3 and alert and alert.payload["attempt_count"] == 3
        assert s.scalar(select(Position).where(Position.id == p.id)).quantity == 10
        assert (
            s.scalar(
                select(func.count())
                .select_from(Trade)
                .where(Trade.instrument_id == i.id, Trade.side == "SELL")
            )
            == 0
        )


def test_repeated_eod_retry_exhaustion_updates_existing_failure_alert():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _snapshot(s, i, "102")
        _run(s, AlwaysFail())
        first = s.scalar(
            select(Alert).where(
                Alert.instrument_id == i.id,
                Alert.alert_type == "EOD_EXIT_FAILED",
                Alert.status == "open",
            )
        )
        _run(s, AlwaysFail())
        second = s.scalar(
            select(Alert).where(
                Alert.instrument_id == i.id,
                Alert.alert_type == "EOD_EXIT_FAILED",
                Alert.status == "open",
            )
        )
        assert first.id == second.id


def test_successful_eod_recovery_resolves_existing_failure_alert():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _snapshot(s, i, "102")
        _run(s, AlwaysFail(p.id))
        failed = s.scalar(
            select(Alert).where(
                Alert.instrument_id == i.id,
                Alert.alert_type == "EOD_EXIT_FAILED",
                Alert.status == "open",
            )
        )
        assert failed is not None
        from app.paper_trading.service import exit_position

        _run(s, exit_position)
        resolved = s.get(Alert, failed.id)
        assert resolved.status == "resolved" and resolved.resolved_at is not None
        assert s.scalar(select(Position).where(Position.id == p.id)).quantity == 0


def test_post_recovery_eod_rerun_is_financially_idempotent():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _snapshot(s, i, "102")
        _run(s, AlwaysFail(p.id))
        from app.paper_trading.service import exit_position

        _run(s, exit_position)
        before = [
            s.scalar(select(func.count()).select_from(t).where(t.instrument_id == i.id))
            for t in (Order, Trade)
        ]
        _run(s, exit_position)
        after = [
            s.scalar(select(func.count()).select_from(t).where(t.instrument_id == i.id))
            for t in (Order, Trade)
        ]
        assert before == after


def test_retry_failure_after_order_flush_rolls_back_provisional_rows():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _snapshot(s, i, "102")
        executor = HookFail(p.id, "AFTER_ORDER_FLUSH")
        _run(s, executor)
        assert (
            executor.calls == 3
            and s.scalar(select(Position).where(Position.id == p.id)).quantity == 10
        )
        assert (
            s.scalar(
                select(func.count())
                .select_from(Order)
                .where(Order.instrument_id == i.id, Order.side == "SELL")
            )
            == 0
        )


def test_retry_failure_after_fill_flush_rolls_back_all_financial_rows():
    with SessionLocal.begin() as s:
        i, p = _scenario(s)
        _snapshot(s, i, "102")
        executor = HookFail(p.id, "AFTER_FILL_FLUSH")
        _run(s, executor)
        assert (
            executor.calls == 3
            and s.scalar(select(Position).where(Position.id == p.id)).quantity == 10
        )
        assert (
            s.scalar(
                select(func.count())
                .select_from(Trade)
                .where(Trade.instrument_id == i.id, Trade.side == "SELL")
            )
            == 0
        )


def test_scheduled_job_bootstrap_does_not_execute_eod_handler():
    with SessionLocal.begin() as s:
        from app.scheduler.service import ensure_jobs

        before = s.scalar(select(func.count()).select_from(JobRun))
        ensure_jobs(s)
        assert s.scalar(select(func.count()).select_from(JobRun)) == before


def test_repeated_injected_time_runs_create_unique_job_runs():
    with SessionLocal.begin() as s:
        from app.scheduler.service import ensure_jobs

        ensure_jobs(s)
        t = datetime(2026, 7, 20, 9, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        run_job(s, "EOD_POSITION_EXIT", evaluation_time=t, eod_policy=EodExitPolicy())
        run_job(s, "EOD_POSITION_EXIT", evaluation_time=t, eod_policy=EodExitPolicy())
        rows = s.scalars(
            select(JobRun)
            .where(JobRun.job_name == "EOD_POSITION_EXIT")
            .order_by(JobRun.created_at.desc())
            .limit(2)
        ).all()
        assert len(rows) == 2 and rows[0].job_key != rows[1].job_key
