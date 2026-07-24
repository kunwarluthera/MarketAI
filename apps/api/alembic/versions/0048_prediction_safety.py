"""Layer 3.6.3C prediction safety gates foundation."""
from alembic import op
import sqlalchemy as sa

revision = "0048_prediction_safety"
down_revision = "0047_calibration_governance"


def upgrade():
    op.create_table("ml_prediction_safety_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), nullable=False, unique=True), sa.Column("version", sa.String(24), nullable=False), sa.Column("enabled", sa.Boolean, nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_prediction_safety_results", sa.Column("id", sa.String(36), primary_key=True), sa.Column("safety_identity", sa.String(64), nullable=False, unique=True), sa.Column("prediction_identity", sa.String(64), nullable=False), sa.Column("decision", sa.String(32), nullable=False), sa.Column("rule_results", sa.JSON, nullable=False), sa.Column("result_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_prediction_safety_manifests", sa.Column("id", sa.String(36), primary_key=True), sa.Column("manifest_identity", sa.String(64), nullable=False, unique=True), sa.Column("safety_identity", sa.String(64), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("manifest_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_prediction_safety_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("event_identity", sa.String(64), nullable=False, unique=True), sa.Column("safety_identity", sa.String(64), nullable=False), sa.Column("event_type", sa.String(48), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_prediction_safety_policies (id, policy_code, version, enabled, payload, created_at) VALUES ('safety-policy-v1', 'CONTROLLED_PREDICTION_SAFETY_V1', '1', true, '{}', CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))


def downgrade():
    op.drop_table("ml_prediction_safety_events")
    op.drop_table("ml_prediction_safety_manifests")
    op.drop_table("ml_prediction_safety_results")
    op.drop_table("ml_prediction_safety_policies")
