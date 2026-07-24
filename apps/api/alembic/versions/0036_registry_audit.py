"""Layer 3.5.6 immutable registry audit reports."""

from alembic import op
import sqlalchemy as sa

revision = "0036_registry_audit"
down_revision = "0035_role_assignments"


def upgrade():
    op.create_table(
        "registry_audit_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("report_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("scope", sa.String(80), nullable=False),
        sa.Column("replayable", sa.Boolean, nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("findings", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("registry_audit_reports")
