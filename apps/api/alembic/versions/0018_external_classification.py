"""Layer 2.4 deterministic event classification."""
from alembic import op
import sqlalchemy as sa
revision = "0018_external_classification"
down_revision = "0017_entity_mappings"
def upgrade():
    op.create_table("external_classifications", sa.Column("id", sa.String(36), primary_key=True), sa.Column("external_item_id", sa.String(36), nullable=False), sa.Column("category_code", sa.String(64), nullable=False), sa.Column("category_version", sa.String(16), nullable=False), sa.Column("impact", sa.String(16), nullable=False), sa.Column("confirmation", sa.String(16), nullable=False), sa.Column("rule_strength", sa.Numeric(8,6), nullable=False), sa.Column("matched_phrases", sa.JSON, nullable=False), sa.Column("excluded_phrases", sa.JSON, nullable=False), sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_external_classification_lookup", "external_classifications", ["external_item_id", "category_code", "evaluated_at"])
def downgrade():
    op.drop_index("ix_external_classification_lookup", table_name="external_classifications"); op.drop_table("external_classifications")
