"""Layer 3.2 immutable outcomes and labels."""

from alembic import op
import sqlalchemy as sa

revision = "0026_ml_labels"
down_revision = "0025_ml_datasets"


def upgrade():
    op.create_table(
        "ml_label_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("row_identity", sa.String(64), nullable=False),
        sa.Column("outcome_code", sa.String(80), nullable=False),
        sa.Column("outcome_version", sa.String(32), nullable=False),
        sa.Column("label_code", sa.String(80), nullable=False),
        sa.Column("label_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("feature_cutoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True)),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("lineage", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("ml_label_records")
