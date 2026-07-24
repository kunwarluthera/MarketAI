"""Layer 3.6.5B governed local attribution."""
from alembic import op
import sqlalchemy as sa
revision = "0055_attribution"
down_revision = "0054_explainability"
def upgrade():
    op.create_table("ml_prediction_attribution_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), unique=True), sa.Column("enabled", sa.Boolean), sa.Column("algorithm_priority", sa.JSON), sa.Column("normalize_scores", sa.Boolean), sa.Column("precision_digits", sa.Integer), sa.Column("checksum", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_prediction_attribution_algorithms", sa.Column("id", sa.String(36), primary_key=True), sa.Column("algorithm", sa.String(80), unique=True), sa.Column("enabled", sa.Boolean), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_prediction_local_explanations", sa.Column("id", sa.String(36), primary_key=True), sa.Column("explanation_identity", sa.String(64), unique=True), sa.Column("explainability_id", sa.String(64)), sa.Column("prediction_identity", sa.String(64)), sa.Column("algorithm", sa.String(80)), sa.Column("payload", sa.JSON), sa.Column("checksum", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_prediction_local_attributions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("explanation_identity", sa.String(64)), sa.Column("feature_name", sa.String(128)), sa.Column("feature_index", sa.Integer), sa.Column("payload", sa.JSON), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_prediction_attribution_policies (id, policy_code, enabled, algorithm_priority, normalize_scores, precision_digits, checksum, created_at) VALUES ('attribution-policy-v1', 'CONTROLLED_LOCAL_ATTRIBUTION_V1', true, '{\"algorithms\": [\"Tree SHAP\", \"Permutation Attribution\", \"Integrated Gradients placeholder\", \"Kernel SHAP placeholder\"]}', true, 8, 'seeded-attribution-v1', CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))
def downgrade():
    for table in ("ml_prediction_local_attributions", "ml_prediction_local_explanations", "ml_prediction_attribution_algorithms", "ml_prediction_attribution_policies"):
        op.drop_table(table)
