"""Layer 3.6.5C governed global explainability."""
from alembic import op
import sqlalchemy as sa
revision = "0056_global_explainability"
down_revision = "0055_attribution"
def upgrade():
    op.create_table("ml_prediction_global_explainability_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), unique=True), sa.Column("enabled", sa.Boolean), sa.Column("minimum_sample_size", sa.Integer), sa.Column("aggregation_strategy", sa.String(32)), sa.Column("top_feature_limit", sa.Integer), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_prediction_global_explanations", sa.Column("id", sa.String(36), primary_key=True), sa.Column("explanation_identity", sa.String(64), unique=True), sa.Column("dataset_identity", sa.String(64)), sa.Column("model_identity", sa.String(64)), sa.Column("payload", sa.JSON), sa.Column("checksum", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_prediction_global_feature_importance", sa.Column("id", sa.String(36), primary_key=True), sa.Column("explanation_identity", sa.String(64)), sa.Column("feature_name", sa.String(128)), sa.Column("payload", sa.JSON), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_prediction_global_stability", sa.Column("id", sa.String(36), primary_key=True), sa.Column("explanation_identity", sa.String(64), unique=True), sa.Column("payload", sa.JSON), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_prediction_global_explainability_policies (id, policy_code, enabled, minimum_sample_size, aggregation_strategy, top_feature_limit, created_at) VALUES ('global-policy-v1', 'CONTROLLED_GLOBAL_EXPLAINABILITY_V1', true, 1, 'mean_absolute', 20, CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))
def downgrade():
    for table in ("ml_prediction_global_stability", "ml_prediction_global_feature_importance", "ml_prediction_global_explanations", "ml_prediction_global_explainability_policies"):
        op.drop_table(table)
