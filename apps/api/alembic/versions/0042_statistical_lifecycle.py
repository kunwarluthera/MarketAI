"""Layer 3.6.3B immutable lifecycle corrections."""
from alembic import op
import sqlalchemy as sa

revision = "0042_statistical_lifecycle"
down_revision = "0041_statistical_audit"


def upgrade():
    op.create_table("ml_statistical_validation_lifecycle", sa.Column("id", sa.String(36), primary_key=True), sa.Column("lifecycle_identity", sa.String(64), nullable=False, unique=True), sa.Column("request_identity", sa.String(64), nullable=False), sa.Column("action", sa.String(24), nullable=False), sa.Column("reason", sa.String(300), nullable=False), sa.Column("actor_identity", sa.String(120), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)


def downgrade():
    op.drop_table("ml_statistical_validation_lifecycle")
