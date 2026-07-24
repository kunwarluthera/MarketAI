"""Durable scheduler definitions."""
from alembic import op
import sqlalchemy as sa

revision = "0004_scheduler"
down_revision = "0003_sell_order_approval"

def upgrade() -> None:
    op.create_table(
        "scheduled_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_type", sa.String(64), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("interval_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="idle"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("lock_owner", sa.String(100)),
        sa.Column("lock_acquired_at", sa.DateTime(timezone=True)),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scheduled_jobs_next_run_at", "scheduled_jobs", ["next_run_at"])

def downgrade() -> None:
    op.drop_index("ix_scheduled_jobs_next_run_at", table_name="scheduled_jobs")
    op.drop_table("scheduled_jobs")
