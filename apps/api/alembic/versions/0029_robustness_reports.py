"""Layer 3.4.3 historical robustness reports."""

from alembic import op
import sqlalchemy as sa

revision = "0029_robustness_reports"
down_revision = "0028_metric_reports"


def upgrade():
    op.create_table(
        "robustness_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("summary_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("validation_id", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("lineage", sa.JSON, nullable=False),
        sa.Column("historical_only", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("robustness_reports")
