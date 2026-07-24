"""Layer 3.7.4 governed benchmark comparisons."""
from alembic import op
import sqlalchemy as sa
revision = "0064_benchmark"
down_revision = "0063_calibration"
def upgrade():
    op.create_table("ml_benchmark_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), unique=True), sa.Column("enabled", sa.Boolean), sa.Column("payload", sa.JSON), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_benchmark_comparisons", sa.Column("id", sa.String(36), primary_key=True), sa.Column("benchmark_id", sa.String(64), unique=True), sa.Column("left_model", sa.String(64)), sa.Column("right_model", sa.String(64)), sa.Column("dataset_id", sa.String(64)), sa.Column("payload", sa.JSON), sa.Column("checksum", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_benchmark_policies (id, policy_code, enabled, payload, created_at) VALUES ('benchmark-policy-v1', 'CONTROLLED_BENCHMARK_V1', true, '{}', CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))
def downgrade():
    op.drop_table("ml_benchmark_comparisons")
    op.drop_table("ml_benchmark_policies")
