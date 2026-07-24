"""Layer 3.6.4 durable partition, retry and control records."""
from alembic import op
import sqlalchemy as sa

revision = "0052_batch_controls"
down_revision = "0051_batch_prediction"

def upgrade():
    op.create_table("ml_batch_prediction_partitions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("batch_id", sa.String(64), nullable=False), sa.Column("partition_number", sa.Integer, nullable=False), sa.Column("first_ordinal", sa.Integer, nullable=False), sa.Column("last_ordinal", sa.Integer, nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_batch_prediction_attempts", sa.Column("id", sa.String(36), primary_key=True), sa.Column("item_key", sa.String(128), nullable=False), sa.Column("attempt_number", sa.Integer, nullable=False), sa.Column("stage", sa.String(48), nullable=False), sa.Column("outcome", sa.String(32), nullable=False), sa.Column("failure_code", sa.String(64)), sa.Column("retryable", sa.Boolean, nullable=False), sa.Column("attempt_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_batch_prediction_checkpoints", sa.Column("id", sa.String(36), primary_key=True), sa.Column("batch_id", sa.String(64), nullable=False), sa.Column("item_key", sa.String(128)), sa.Column("checkpoint_type", sa.String(64), nullable=False), sa.Column("sequence", sa.Integer, nullable=False), sa.Column("state_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_batch_prediction_cancellations", sa.Column("id", sa.String(36), primary_key=True), sa.Column("batch_id", sa.String(64), unique=True, nullable=False), sa.Column("requested_by", sa.String(128), nullable=False), sa.Column("reason", sa.String(300), nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)

def downgrade():
    for table in ("ml_batch_prediction_cancellations", "ml_batch_prediction_checkpoints", "ml_batch_prediction_attempts", "ml_batch_prediction_partitions"):
        op.drop_table(table)
