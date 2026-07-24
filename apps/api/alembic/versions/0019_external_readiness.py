"""Layer 2.4 external intelligence readiness and expiry."""
from alembic import op
import sqlalchemy as sa
revision = "0019_external_readiness"
down_revision = "0018_external_classification"
def upgrade():
    op.create_table("external_intelligence_readiness", sa.Column("id", sa.String(36), primary_key=True), sa.Column("provider", sa.String(32), nullable=False), sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("status", sa.String(16), nullable=False), sa.Column("blocking_reasons", sa.JSON, nullable=False), sa.Column("warning_reasons", sa.JSON, nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_external_readiness_lookup", "external_intelligence_readiness", ["provider", "evaluated_at", "status", "expires_at"])
def downgrade():
    op.drop_index("ix_external_readiness_lookup", table_name="external_intelligence_readiness"); op.drop_table("external_intelligence_readiness")
