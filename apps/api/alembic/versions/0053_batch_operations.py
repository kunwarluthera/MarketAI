"""Layer 3.6.4 worker leases and replay lineage."""
from alembic import op
import sqlalchemy as sa
revision = "0053_batch_operations"
down_revision = "0052_batch_controls"

def upgrade():
    op.create_table("ml_batch_prediction_worker_leases", sa.Column("id", sa.String(36), primary_key=True), sa.Column("batch_id", sa.String(64), nullable=False), sa.Column("partition_id", sa.String(36), nullable=False), sa.Column("worker_key", sa.String(128), nullable=False), sa.Column("lease_token_hash", sa.String(64), nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_batch_prediction_replays", sa.Column("id", sa.String(36), primary_key=True), sa.Column("source_batch_id", sa.String(64), nullable=False), sa.Column("replay_batch_id", sa.String(64), unique=True, nullable=False), sa.Column("mode", sa.String(32), nullable=False), sa.Column("checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)

def downgrade():
    op.drop_table("ml_batch_prediction_replays")
    op.drop_table("ml_batch_prediction_worker_leases")
