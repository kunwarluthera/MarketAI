"""Persist deterministic simulated market snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "0007_market_snapshots"
down_revision = "0006_risk_rules"

def upgrade() -> None:
    op.create_table("market_snapshots",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("instrument_id", sa.String(36), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("price", sa.Numeric(20, 4), nullable=False), sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("exchange_timestamp", sa.DateTime(timezone=True), nullable=False), sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(32), nullable=False), sa.Column("scenario", sa.String(32), nullable=False), sa.Column("occurrence_key", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("instrument_id", "occurrence_key"), sa.CheckConstraint("price > 0 AND volume >= 0"))
    op.create_index("ix_market_snapshots_exchange_timestamp", "market_snapshots", ["exchange_timestamp"])

def downgrade() -> None:
    op.drop_table("market_snapshots")
