"""Layer 3.6.3A prediction validation governance."""
from alembic import op
import sqlalchemy as sa
from hashlib import sha256

revision = "0039_prediction_validation"
down_revision = "0038_offline_predictions"

def upgrade():
    def common():
        return [sa.Column("id", sa.String(36), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False)]
    op.create_table("ml_prediction_validation_policies", *common(), sa.Column("validation_policy_code", sa.String(80), nullable=False), sa.Column("version", sa.String(24), nullable=False), sa.Column("description", sa.String(300), nullable=False), sa.Column("enabled", sa.Boolean, nullable=False), sa.Column("allowed_prediction_statuses", sa.JSON, nullable=False), sa.Column("required_prediction_policy", sa.JSON, nullable=False), sa.Column("required_output_contract", sa.JSON, nullable=False), sa.Column("required_model_status", sa.String(40), nullable=False), sa.Column("required_manifest_version", sa.String(40), nullable=False), sa.Column("validation_mode", sa.String(40), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("validation_policy_code"), if_not_exists=True)
    op.create_table("ml_prediction_validation_requests", *common(), sa.Column("request_identity", sa.String(64), nullable=False, unique=True), sa.Column("prediction_result_identity", sa.String(64), nullable=False), sa.Column("validation_policy", sa.String(100), nullable=False), sa.Column("requested_by", sa.String(120), nullable=False), sa.Column("request_reason", sa.String(300), nullable=False), sa.Column("request_status", sa.String(24), nullable=False, ) , if_not_exists=True)
    op.create_table("ml_prediction_validation_rules", *common(), sa.Column("rule_code", sa.String(80), nullable=False, unique=True), sa.Column("description", sa.String(300), nullable=False), sa.Column("enabled", sa.Boolean, nullable=False), if_not_exists=True)
    op.create_table("ml_prediction_validation_results", *common(), sa.Column("request_identity", sa.String(64), nullable=False, unique=True), sa.Column("decision", sa.String(32), nullable=False), sa.Column("eligibility", sa.String(32), nullable=False), sa.Column("rule_outcomes", sa.JSON, nullable=False), if_not_exists=True)
    op.create_table("ml_prediction_validation_manifests", *common(), sa.Column("manifest_identity", sa.String(64), nullable=False, unique=True), sa.Column("request_identity", sa.String(64), nullable=False), sa.Column("prediction_identity", sa.String(64), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("manifest_checksum", sa.String(64), nullable=False), if_not_exists=True)
    op.create_table("ml_prediction_validation_events", *common(), sa.Column("event_identity", sa.String(64), nullable=False, unique=True), sa.Column("request_identity", sa.String(64), nullable=False), sa.Column("event_type", sa.String(40), nullable=False), sa.Column("payload", sa.JSON, nullable=False), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_prediction_validation_policies (id, validation_policy_code, version, description, enabled, allowed_prediction_statuses, required_prediction_policy, required_output_contract, required_model_status, required_manifest_version, validation_mode, created_at, updated_at) VALUES ('validation-policy-v1', 'CONTROLLED_PREDICTION_VALIDATION_V1', '1', 'Deterministic controlled offline prediction validation', true, '[\"completed\"]', '{}', '{}', 'approved', '1', 'deterministic', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))
    rules = ("prediction_exists", "manifest_exists", "output_validated", "prediction_checksum_valid", "manifest_checksum_valid", "model_approved", "policy_enabled", "prediction_immutable", "prediction_not_invalidated", "prediction_not_superseded")
    for rule in rules:
        rule_id = ("validation-" + sha256(rule.encode()).hexdigest())[:36]
        op.execute(sa.text("INSERT INTO ml_prediction_validation_rules (id, rule_code, description, enabled, created_at) VALUES (:id, :code, :description, true, CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING").bindparams(id=rule_id, code=rule, description="Deterministic validation rule: " + rule))

def downgrade():
    op.drop_table("ml_prediction_validation_events")
    op.drop_table("ml_prediction_validation_manifests")
    op.drop_table("ml_prediction_validation_results")
    op.drop_table("ml_prediction_validation_rules")
    op.drop_table("ml_prediction_validation_requests")
    op.drop_table("ml_prediction_validation_policies")
