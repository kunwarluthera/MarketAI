"""Layer 3.5.1 immutable registry definitions."""

from alembic import op
import sqlalchemy as sa

revision = "0031_model_registry_definitions"
down_revision = "0030_validation_decisions"


def upgrade():
    op.create_table(
        "model_registry_definitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("definition_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("definition_code", sa.String(80), nullable=False),
        sa.Column("definition_version", sa.String(32), nullable=False),
        sa.Column("definition_type", sa.String(40), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("model_registry_definitions")
