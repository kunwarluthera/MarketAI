"""Layer 3.7.2 governed metric computation."""
from alembic import op
import sqlalchemy as sa
revision = "0061_metrics"
down_revision = "0060_evaluation_governance"
def upgrade():
    op.create_table("ml_metric_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), unique=True), sa.Column("enabled", sa.Boolean), sa.Column("payload", sa.JSON), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_metric_results", sa.Column("id", sa.String(36), primary_key=True), sa.Column("evaluation_id", sa.String(64)), sa.Column("metric", sa.String(48)), sa.Column("family", sa.String(32)), sa.Column("payload", sa.JSON), sa.Column("result_checksum", sa.String(64), unique=True), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_metric_policies (id, policy_code, enabled, payload, created_at) VALUES ('metrics-policy-v1', 'CONTROLLED_METRICS_V1', true, '{\"metrics\": [\"accuracy\", \"mae\", \"mse\", \"rmse\"]}', CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))
def downgrade():
    op.drop_table("ml_metric_results")
    op.drop_table("ml_metric_policies")
