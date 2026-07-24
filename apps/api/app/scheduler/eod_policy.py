from dataclasses import dataclass, field
from datetime import date, time
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class EodExitPolicy:
    market_timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("Asia/Kolkata"))
    cutoff_time: time = time(15, 20)
    max_retry_attempts: int = 3
    market_data_freshness_seconds: int = 300
    holidays: frozenset[date] = frozenset()

    def is_trading_day(self, value: date) -> bool:
        return value.weekday() < 5 and value not in self.holidays


class RetryableEodExitError(RuntimeError):
    """Failure that may be retried without committing financial effects."""
