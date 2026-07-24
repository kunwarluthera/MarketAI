"""Layer 2.1 rejection audit and revision support."""
from alembic import op
import sqlalchemy as sa

revision = "0011_intel_rejections"
down_revision = "0010_intel_calendar_provider"


def upgrade() -> None:
    bind = op.get_bind()
    old = bind.exec_driver_sql("""SELECT conname FROM pg_constraint WHERE conrelid='intelligence_candles'::regclass AND contype='u' AND pg_get_constraintdef(oid) LIKE '%%instrument_id%%source%%'""").scalar()
    if old:
        bind.exec_driver_sql(f'ALTER TABLE intelligence_candles DROP CONSTRAINT "{old}"')
    op.create_unique_constraint("uq_intel_candle_identity_revision", "intelligence_candles", ["instrument_id", "interval", "started_at", "source", "revision"])
    op.add_column("intelligence_candles", sa.Column("is_authoritative", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_intel_candles_authoritative", "intelligence_candles", ["instrument_id", "interval", "started_at", "source", "is_authoritative"])
    op.create_table(
        "intelligence_candle_rejections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("instrument_id", sa.String(36)),
        sa.Column("interval", sa.String(8), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", sa.JSON, nullable=False),
        sa.Column("error_codes", sa.JSON, nullable=False),
        sa.Column("correlation_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("intelligence_candle_rejections")
    op.drop_index("ix_intel_candles_authoritative", table_name="intelligence_candles")
    op.drop_column("intelligence_candles", "is_authoritative")
