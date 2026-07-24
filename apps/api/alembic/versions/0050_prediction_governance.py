"""Layer 3.6.3D prediction governance foundation."""
from alembic import op
import sqlalchemy as sa

revision = "0050_prediction_governance"
down_revision = "0049_safety_evidence"


def upgrade():
    op.create_table("ml_prediction_governance_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), nullable=False, unique=True), sa.Column("version", sa.String(24), nullable=False), sa.Column("enabled", sa.Boolean, nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_prediction_governance_decisions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("governance_identity", sa.String(64), nullable=False, unique=True), sa.Column("prediction_identity", sa.String(64), nullable=False), sa.Column("decision", sa.String(32), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("decision_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_prediction_governance_manifests", sa.Column("id", sa.String(36), primary_key=True), sa.Column("manifest_identity", sa.String(64), nullable=False, unique=True), sa.Column("governance_identity", sa.String(64), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("manifest_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_prediction_governance_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("event_identity", sa.String(64), nullable=False, unique=True), sa.Column("governance_identity", sa.String(64), nullable=False), sa.Column("event_type", sa.String(48), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_prediction_governance_policies (id, policy_code, version, enabled, payload, created_at) VALUES ('governance-policy-v1', 'CONTROLLED_VALIDATION_GOVERNANCE_V1', '1', true, '{}', CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))


def downgrade():
    op.drop_table("ml_prediction_governance_events")
    op.drop_table("ml_prediction_governance_manifests")
    op.drop_table("ml_prediction_governance_decisions")
    op.drop_table("ml_prediction_governance_policies")
