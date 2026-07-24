"""Layer 2.4 correction and retraction lineage."""
from alembic import op
import sqlalchemy as sa
revision = "0020_external_relations"
down_revision = "0019_external_readiness"
def upgrade():
    op.create_table("external_item_relations", sa.Column("id", sa.String(36), primary_key=True), sa.Column("source_item_id", sa.String(36), nullable=False), sa.Column("target_item_id", sa.String(36), nullable=False), sa.Column("relation_type", sa.String(32), nullable=False), sa.Column("rule_version", sa.String(16), nullable=False), sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("details", sa.JSON, nullable=False))
    op.create_index("ix_external_relations_lookup", "external_item_relations", ["source_item_id", "target_item_id", "relation_type"])
def downgrade():
    op.drop_index("ix_external_relations_lookup", table_name="external_item_relations"); op.drop_table("external_item_relations")
