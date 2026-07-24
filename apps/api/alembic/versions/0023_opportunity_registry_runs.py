"""Layer 2.5 rule registry and discovery runs."""

from alembic import op
import sqlalchemy as sa

revision = "0023_opportunity_registry_runs"
down_revision = "0022_opportunities"


def upgrade():
    op.create_table(
        "opportunity_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_code", sa.String(80), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("parameters", sa.JSON, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("rule_code", "rule_version"),
    )
    op.create_table(
        "opportunity_discovery_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("instrument_count", sa.Integer, nullable=False),
        sa.Column("opportunity_count", sa.Integer, nullable=False),
        sa.Column("lineage", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("opportunity_discovery_runs")
    op.drop_table("opportunity_rules")
