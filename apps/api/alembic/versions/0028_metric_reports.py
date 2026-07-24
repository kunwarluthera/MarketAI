"""Layer 3.4.2 immutable aggregate reports."""

from alembic import op
import sqlalchemy as sa

revision = "0028_metric_reports"
down_revision = "0027_ml_training_runs"


def upgrade():
    op.create_table(
        "metric_aggregation_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("report_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("validation_id", sa.String(64), nullable=False),
        sa.Column("fold_count", sa.Integer, nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("lineage", sa.JSON, nullable=False),
        sa.Column("research_only", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("metric_aggregation_reports")
