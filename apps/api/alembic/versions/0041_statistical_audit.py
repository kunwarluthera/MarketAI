"""Layer 3.6.3B immutable manifests and event ledger."""
from alembic import op
import sqlalchemy as sa

revision = "0041_statistical_audit"
down_revision = "0040_statistical_validation"


def upgrade():
    op.create_table("ml_statistical_validation_manifests", sa.Column("id", sa.String(36), primary_key=True), sa.Column("manifest_identity", sa.String(64), nullable=False, unique=True), sa.Column("request_identity", sa.String(64), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("manifest_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_statistical_validation_events", sa.Column("id", sa.String(36), primary_key=True), sa.Column("event_identity", sa.String(64), nullable=False, unique=True), sa.Column("request_identity", sa.String(64), nullable=False), sa.Column("event_type", sa.String(48), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)


def downgrade():
    op.drop_table("ml_statistical_validation_events")
    op.drop_table("ml_statistical_validation_manifests")
