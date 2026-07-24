"""Layer 3.3 immutable research training runs."""

from alembic import op
import sqlalchemy as sa

revision = "0027_ml_training_runs"
down_revision = "0026_ml_labels"


def upgrade():
    op.create_table(
        "ml_training_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("training_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("dataset_identity", sa.String(64), nullable=False),
        sa.Column("label_spec", sa.String(100), nullable=False),
        sa.Column("algorithm", sa.String(80), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("metrics", sa.JSON, nullable=False),
        sa.Column("lineage", sa.JSON, nullable=False),
        sa.Column("research_only", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("ml_training_runs")
