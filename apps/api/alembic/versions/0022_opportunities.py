"""Layer 2.5 auditable research opportunities."""

from alembic import op
import sqlalchemy as sa

revision = "0022_opportunities"
down_revision = "0021_classification_importance"


def upgrade():
    op.create_table(
        "opportunity_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("instrument_id", sa.String(36), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("orientation", sa.String(32), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("blockers", sa.JSON, nullable=False),
        sa.Column("cautions", sa.JSON, nullable=False),
        sa.Column("contributions", sa.JSON, nullable=False),
        sa.Column("lineage", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("instrument_id", "evaluated_at", "rule_version"),
    )
    op.create_index(
        "ix_opportunity_instrument_time", "opportunity_records", ["instrument_id", "evaluated_at"]
    )


def downgrade():
    op.drop_index("ix_opportunity_instrument_time", table_name="opportunity_records")
    op.drop_table("opportunity_records")
