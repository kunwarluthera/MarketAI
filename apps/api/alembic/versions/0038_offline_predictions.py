"""Layer 3.6.2 immutable offline prediction records."""

from alembic import op
import sqlalchemy as sa

revision = "0038_offline_predictions"
down_revision = "0037_model_loads"


def upgrade():
    op.create_table(
        "offline_prediction_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("prediction_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("lineage", sa.JSON, nullable=False),
        sa.Column("offline_only", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("offline_prediction_records")
