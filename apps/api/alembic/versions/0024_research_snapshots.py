"""Layer 2.6 canonical point-in-time research snapshots."""

from alembic import op
import sqlalchemy as sa

revision = "0024_research_snapshots"
down_revision = "0023_opportunity_registry_runs"


def upgrade():
    op.create_table(
        "research_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("snapshot_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("instrument_id", sa.String(36), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("lineage", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_research_snapshot_instrument_time",
        "research_snapshots",
        ["instrument_id", "evaluated_at"],
    )


def downgrade():
    op.drop_index("ix_research_snapshot_instrument_time", table_name="research_snapshots")
    op.drop_table("research_snapshots")
