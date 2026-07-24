from datetime import UTC, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.common.models import Position, Trade

IST = ZoneInfo("Asia/Kolkata")


class DailyPnLService:
    """Authoritative Decimal daily P&L derived only from PostgreSQL records."""

    def __init__(self, session: Session, at: datetime | None = None):
        self.session = session
        self.at = (at or datetime.now(UTC)).astimezone(IST)

    def calculate(self) -> dict:
        start = datetime.combine(self.at.date(), time.min, tzinfo=IST).astimezone(UTC)
        trades = self.session.scalars(select(Trade).where(Trade.created_at >= start)).all()
        realised = sum(
            (Decimal(t.realised_pnl or 0) for t in trades if t.side == "SELL"), Decimal(0)
        )
        charges = sum((Decimal(t.charges or 0) for t in trades), Decimal(0))
        positions = self.session.scalars(select(Position).where(Position.quantity > 0)).all()
        unrealised = sum(
            ((p.current_price - p.average_price) * p.quantity for p in positions), Decimal(0)
        )
        total = realised + unrealised - charges
        loss = abs(total) if total < 0 else Decimal(0)
        return {
            "trading_date_ist": self.at.date().isoformat(),
            "daily_realised_pnl": str(realised),
            "daily_unrealised_pnl": str(unrealised),
            "daily_charges": str(charges),
            "daily_total_pnl": str(total),
            "daily_loss_amount": str(loss),
            "daily_loss_usage_percent": str(
                (loss / Decimal("1000000") * 100).quantize(Decimal("0.0001"))
            ),
            "calculated_at": datetime.now(UTC).isoformat(),
        }
