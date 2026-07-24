"""Layer 3.6.1 controlled model-load manifests."""

from alembic import op
import sqlalchemy as sa

revision = "0037_model_loads"
down_revision = "0036_registry_audit"


def upgrade():
    op.create_table(
        "model_load_manifests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("load_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("version_identity", sa.String(64), nullable=False),
        sa.Column("handle_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("model_load_manifests")
