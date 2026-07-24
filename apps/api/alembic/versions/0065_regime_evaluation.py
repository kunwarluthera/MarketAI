"""Layer 3.7.5 governed regime and segment evaluation."""
from alembic import op
import sqlalchemy as sa
revision = "0065_regime_evaluation"
down_revision = "0064_benchmark"
def upgrade():
    op.create_table("ml_regime_evaluation_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), unique=True), sa.Column("enabled", sa.Boolean), sa.Column("minimum_samples", sa.Integer), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_regime_evaluations", sa.Column("id", sa.String(36), primary_key=True), sa.Column("evaluation_identity", sa.String(64), unique=True), sa.Column("source_evaluation_id", sa.String(64)), sa.Column("payload", sa.JSON), sa.Column("checksum", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_regime_evaluation_policies (id, policy_code, enabled, minimum_samples, created_at) VALUES ('regime-policy-v1', 'CONTROLLED_REGIME_EVALUATION_V1', true, 1, CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))
def downgrade():
    op.drop_table("ml_regime_evaluations")
    op.drop_table("ml_regime_evaluation_policies")
