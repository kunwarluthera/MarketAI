"""Layer 3.5.5 immutable champion/challenger assignments."""
from alembic import op
import sqlalchemy as sa
revision = "0035_role_assignments"
down_revision = "0034_promotion_requests"
def upgrade():
    op.create_table("model_role_assignments", sa.Column("id", sa.String(36), primary_key=True), sa.Column("assignment_identity", sa.String(64), nullable=False, unique=True), sa.Column("scope", sa.String(80), nullable=False), sa.Column("champion_identity", sa.String(64)), sa.Column("challenger_identities", sa.JSON, nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
def downgrade():
    op.drop_table("model_role_assignments")
