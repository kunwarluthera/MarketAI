"""Layer 3.7.1 offline evaluation governance."""
from alembic import op
import sqlalchemy as sa
revision = "0060_evaluation_governance"
down_revision = "0059_runtime_governance"
def upgrade():
    op.create_table("ml_evaluation_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), unique=True), sa.Column("enabled", sa.Boolean), sa.Column("payload", sa.JSON), sa.Column("checksum", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_evaluation_requests", sa.Column("id", sa.String(36), primary_key=True), sa.Column("evaluation_id", sa.String(64), unique=True), sa.Column("dataset_id", sa.String(64)), sa.Column("model_id", sa.String(64)), sa.Column("status", sa.String(24)), sa.Column("payload", sa.JSON), sa.Column("checksum", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_evaluation_records", sa.Column("id", sa.String(36), primary_key=True), sa.Column("evaluation_id", sa.String(64)), sa.Column("record_type", sa.String(32)), sa.Column("payload", sa.JSON), sa.Column("checksum", sa.String(64), unique=True), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_evaluation_policies (id, policy_code, enabled, payload, checksum, created_at) VALUES ('evaluation-policy-v1', 'CONTROLLED_EVALUATION_V1', true, '{}', 'seeded-evaluation-v1', CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))
def downgrade():
    for table in ("ml_evaluation_records", "ml_evaluation_requests", "ml_evaluation_policies"):
        op.drop_table(table)
