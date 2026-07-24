"""Enforce one authoritative Layer 2.1 candle revision."""
from alembic import op

revision = "0012_intel_authority_index"
down_revision = "0011_intel_rejections"


def upgrade() -> None:
    op.execute("""CREATE UNIQUE INDEX IF NOT EXISTS uq_intel_one_authoritative
        ON intelligence_candles (instrument_id, interval, started_at, source)
        WHERE is_authoritative""")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_intel_one_authoritative")
