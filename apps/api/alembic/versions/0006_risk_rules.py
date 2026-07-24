"""Normalized persisted risk rule results."""
from alembic import op
import sqlalchemy as sa

revision = "0006_risk_rules"
down_revision = "0005_job_leases"

def upgrade() -> None:
    op.create_table("risk_rule_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("risk_evaluation_id", sa.String(36), sa.ForeignKey("risk_evaluations.id"), nullable=False),
        sa.Column("configuration_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("rule_name", sa.String(80), nullable=False), sa.Column("rule_version", sa.String(20), nullable=False),
        sa.Column("threshold", sa.String(80), nullable=False), sa.Column("observed", sa.String(80), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False), sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False), sa.Column("reason_code", sa.String(80), nullable=False),
        sa.Column("message", sa.String(240), nullable=False), sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_risk_rule_results_evaluation", "risk_rule_results", ["risk_evaluation_id"])

def downgrade() -> None:
    op.drop_table("risk_rule_results")
