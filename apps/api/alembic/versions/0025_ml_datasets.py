"""Layer 3.1 immutable dataset manifests."""

from alembic import op
import sqlalchemy as sa

revision = "0025_ml_datasets"
down_revision = "0024_research_snapshots"


def upgrade():
    op.create_table(
        "ml_datasets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dataset_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("dataset_code", sa.String(80), nullable=False),
        sa.Column("dataset_version", sa.String(32), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("row_count", sa.Integer, nullable=False),
        sa.Column("manifest", sa.JSON, nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("ml_datasets")
