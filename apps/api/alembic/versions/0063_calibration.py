"""Layer 3.7.3 governed calibration and reliability."""
from alembic import op
import sqlalchemy as sa
revision = "0063_calibration"
down_revision = "0062_metric_policy_expansion"
def upgrade():
    op.create_table("ml_calibration_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), unique=True), sa.Column("enabled", sa.Boolean), sa.Column("minimum_samples", sa.Integer), sa.Column("maximum_bins", sa.Integer), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_reliability_objects", sa.Column("id", sa.String(36), primary_key=True), sa.Column("evaluation_id", sa.String(64)), sa.Column("payload", sa.JSON), sa.Column("reliability_checksum", sa.String(64), unique=True), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_calibration_policies (id, policy_code, enabled, minimum_samples, maximum_bins, created_at) VALUES ('calibration-policy-v1', 'CONTROLLED_CALIBRATION_V1', true, 1, 10, CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))
def downgrade():
    op.drop_table("ml_reliability_objects")
    op.drop_table("ml_calibration_policies")
