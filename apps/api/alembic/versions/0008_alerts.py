"""Durable market and exit alerts."""
from alembic import op
import sqlalchemy as sa

revision = "0008_alerts"
down_revision = "0007_market_snapshots"

def upgrade() -> None:
    op.create_table("alerts", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("alert_type", sa.String(64), nullable=False), sa.Column("issue_key", sa.String(160), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False), sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason_code", sa.String(80), nullable=False), sa.Column("instrument_id", sa.String(36), sa.ForeignKey("instruments.id")),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)), sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("issue_key", "status"))

def downgrade() -> None:
    op.drop_table("alerts")
