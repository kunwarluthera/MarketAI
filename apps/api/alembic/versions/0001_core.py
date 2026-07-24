"""Core immutable records."""
from alembic import op
import sqlalchemy as sa

revision = "0001_core"
down_revision = None

def upgrade():
    op.create_table("audit_logs", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kind", sa.String(80), nullable=False), sa.Column("entity_id", sa.String(80), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False))
    op.create_table("system_settings", sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=False))

def downgrade():
    op.drop_table("system_settings")
    op.drop_table("audit_logs")
