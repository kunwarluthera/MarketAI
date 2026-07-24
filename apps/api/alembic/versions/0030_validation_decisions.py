"""Layer 3.4.4 immutable validation decisions."""

from alembic import op
import sqlalchemy as sa

revision = "0030_validation_decisions"
down_revision = "0029_robustness_reports"


def upgrade():
    op.create_table(
        "validation_decision_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("decision_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("validation_id", sa.String(64), nullable=False),
        sa.Column("policy_code", sa.String(80), nullable=False),
        sa.Column("policy_version", sa.String(32), nullable=False),
        sa.Column("decision", sa.String(24), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("lineage", sa.JSON, nullable=False),
        sa.Column("research_only", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("validation_decision_records")
