"""Layer 3.6.4 controlled batch prediction foundation."""
from alembic import op
import sqlalchemy as sa

revision = "0051_batch_prediction"
down_revision = "0050_prediction_governance"

def upgrade():
    op.create_table("ml_batch_prediction_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), unique=True, nullable=False), sa.Column("version", sa.String(24), nullable=False), sa.Column("enabled", sa.Boolean, nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_batch_prediction_requests", sa.Column("id", sa.String(36), primary_key=True), sa.Column("batch_id", sa.String(64), unique=True, nullable=False), sa.Column("idempotency_key", sa.String(128), unique=True, nullable=False), sa.Column("requested_by", sa.String(128), nullable=False), sa.Column("policy_code", sa.String(100), nullable=False), sa.Column("universe_type", sa.String(48), nullable=False), sa.Column("universe", sa.JSON, nullable=False), sa.Column("as_of_timestamp", sa.DateTime(timezone=True), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("request_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_batch_prediction_items", sa.Column("id", sa.String(36), primary_key=True), sa.Column("batch_id", sa.String(64), nullable=False), sa.Column("ordinal", sa.Integer, nullable=False), sa.Column("item_key", sa.String(128), unique=True, nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("status", sa.String(40), nullable=False), sa.Column("attempt_count", sa.Integer, nullable=False), sa.Column("outcome", sa.String(32), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_batch_prediction_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("batch_id", sa.String(64), nullable=False), sa.Column("event_identity", sa.String(64), unique=True, nullable=False), sa.Column("event_type", sa.String(48), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_batch_prediction_manifests", sa.Column("id", sa.String(36), primary_key=True), sa.Column("batch_id", sa.String(64), unique=True, nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_batch_prediction_policies (id, policy_code, version, enabled, payload, checksum, created_at) VALUES ('batch-policy-v1', 'CONTROLLED_OFFLINE_BATCH_PREDICTION_V1', '1', true, '{}', 'seeded-batch-policy-v1', CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))

def downgrade():
    for table in ("ml_batch_prediction_manifests", "ml_batch_prediction_events", "ml_batch_prediction_items", "ml_batch_prediction_requests", "ml_batch_prediction_policies"):
        op.drop_table(table)
