"""Layer 3.5.2 immutable model versions."""

from alembic import op
import sqlalchemy as sa

revision = "0032_model_versions"
down_revision = "0031_model_registry_definitions"


def upgrade():
    op.create_table(
        "model_version_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("namespace", sa.String(80), nullable=False),
        sa.Column("model_code", sa.String(80), nullable=False),
        sa.Column("semantic_version", sa.String(32), nullable=False),
        sa.Column("package_identity", sa.String(64), nullable=False),
        sa.Column("predecessor_identity", sa.String(64)),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("model_version_records")
