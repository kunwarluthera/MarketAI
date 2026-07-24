"""Extend the versioned metric policy without editing migration 0061."""
from alembic import op
import sqlalchemy as sa
revision = "0062_metric_policy_expansion"
down_revision = "0061_metrics"
def upgrade():
    op.execute(sa.text("UPDATE ml_metric_policies SET payload = '{\"metrics\": [\"accuracy\", \"precision\", \"recall\", \"f1\", \"mae\", \"mse\", \"rmse\", \"r2\"]}' WHERE policy_code = 'CONTROLLED_METRICS_V1'"))
def downgrade():
    op.execute(sa.text("UPDATE ml_metric_policies SET payload = '{\"metrics\": [\"accuracy\", \"mae\", \"mse\", \"rmse\"]}' WHERE policy_code = 'CONTROLLED_METRICS_V1'"))
