"""Layer 3.6.3C immutable safety gate evidence."""
from alembic import op
import sqlalchemy as sa

revision = "0049_safety_evidence"
down_revision = "0048_prediction_safety"


def upgrade():
    op.create_table("ml_prediction_safety_evidence", sa.Column("id", sa.String(36), primary_key=True), sa.Column("evidence_identity", sa.String(64), nullable=False, unique=True), sa.Column("safety_identity", sa.String(64), nullable=False), sa.Column("evidence_type", sa.String(32), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("evidence_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)


def downgrade():
    op.drop_table("ml_prediction_safety_evidence")
