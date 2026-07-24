"""Persist scheduler lease and heartbeat timestamps."""
from alembic import op
import sqlalchemy as sa

revision = "0005_job_leases"
down_revision = "0004_scheduler"

def upgrade() -> None:
    op.add_column("scheduled_jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
    op.add_column("scheduled_jobs", sa.Column("heartbeat_at", sa.DateTime(timezone=True)))

def downgrade() -> None:
    op.drop_column("scheduled_jobs", "heartbeat_at")
    op.drop_column("scheduled_jobs", "lease_expires_at")
