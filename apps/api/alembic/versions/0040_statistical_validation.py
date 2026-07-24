"""Layer 3.6.3B statistical validation foundation."""
from alembic import op
import sqlalchemy as sa

revision = "0040_statistical_validation"
down_revision = "0039_prediction_validation"


def upgrade():
    op.create_table("ml_statistical_validation_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), nullable=False, unique=True), sa.Column("version", sa.String(24), nullable=False), sa.Column("enabled", sa.Boolean, nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_statistical_validation_requests", sa.Column("id", sa.String(36), primary_key=True), sa.Column("request_identity", sa.String(64), nullable=False, unique=True), sa.Column("parent_validation_request_identity", sa.String(64), nullable=False), sa.Column("prediction_result_identity", sa.String(64), nullable=False), sa.Column("policy_code", sa.String(100), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("request_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_confidence_evidence", sa.Column("id", sa.String(36), primary_key=True), sa.Column("evidence_identity", sa.String(64), nullable=False, unique=True), sa.Column("prediction_result_identity", sa.String(64), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("evidence_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_statistical_validation_results", sa.Column("id", sa.String(36), primary_key=True), sa.Column("request_identity", sa.String(64), nullable=False, unique=True), sa.Column("decision", sa.String(32), nullable=False), sa.Column("rule_results", sa.JSON, nullable=False), sa.Column("result_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_statistical_validation_policies (id, policy_code, version, enabled, payload, created_at) VALUES ('stat-policy-v1', 'CONTROLLED_STATISTICAL_PREDICTION_VALIDATION_V1', '1', true, '{\"minimum_confidence\": 0.5, \"maximum_entropy\": 1.0, \"probability_tolerance\": 1e-9}', CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))


def downgrade():
    op.drop_table("ml_statistical_validation_results")
    op.drop_table("ml_confidence_evidence")
    op.drop_table("ml_statistical_validation_requests")
    op.drop_table("ml_statistical_validation_policies")
