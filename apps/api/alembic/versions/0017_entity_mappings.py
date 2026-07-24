"""Layer 2.4 deterministic entity mappings."""
from alembic import op
import sqlalchemy as sa
revision = "0017_entity_mappings"
down_revision = "0016_entity_aliases"
def upgrade():
    op.create_table("external_entity_mappings", sa.Column("id", sa.String(36), primary_key=True), sa.Column("external_item_id", sa.String(36), nullable=False), sa.Column("entity_type", sa.String(32), nullable=False), sa.Column("entity_id", sa.String(36), nullable=False), sa.Column("relationship_type", sa.String(32), nullable=False), sa.Column("mapping_method", sa.String(32), nullable=False), sa.Column("mapping_score", sa.Numeric(8,6), nullable=False), sa.Column("matched_text", sa.String(256), nullable=False), sa.Column("alias_id", sa.String(36)), sa.Column("is_primary", sa.Boolean, nullable=False), sa.Column("rule_version", sa.String(16), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_entity_mapping_lookup", "external_entity_mappings", ["external_item_id", "entity_type", "entity_id"])
def downgrade():
    op.drop_index("ix_entity_mapping_lookup", table_name="external_entity_mappings"); op.drop_table("external_entity_mappings")
