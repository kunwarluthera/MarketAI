"""Layer 3.7.6 informational promotion readiness."""
from alembic import op
import sqlalchemy as sa
revision = "0066_promotion_readiness"
down_revision = "0065_regime_evaluation"
def upgrade():
    op.create_table("ml_promotion_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), unique=True), sa.Column("enabled", sa.Boolean), sa.Column("payload", sa.JSON), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_promotion_readiness", sa.Column("id", sa.String(36), primary_key=True), sa.Column("readiness_id", sa.String(64), unique=True), sa.Column("model_id", sa.String(64)), sa.Column("dataset_id", sa.String(64)), sa.Column("payload", sa.JSON), sa.Column("checksum", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_promotion_policies (id, policy_code, enabled, payload, created_at) VALUES ('promotion-policy-v1', 'CONTROLLED_PROMOTION_READINESS_V1', true, '{\"required\": [\"evaluation\", \"calibration\", \"benchmark\", \"regime\", \"runtime\", \"explainability\"]}', CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))
def downgrade():
    op.drop_table("ml_promotion_readiness")
    op.drop_table("ml_promotion_policies")
