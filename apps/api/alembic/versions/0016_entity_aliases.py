"""Layer 2.4 deterministic entity aliases."""
from alembic import op
import sqlalchemy as sa
revision = "0016_entity_aliases"
down_revision = "0015_external_intelligence"
def upgrade():
    op.create_table("external_entity_aliases", sa.Column("id", sa.String(36), primary_key=True), sa.Column("entity_type", sa.String(32), nullable=False), sa.Column("entity_id", sa.String(36), nullable=False), sa.Column("alias", sa.String(256), nullable=False), sa.Column("normalized_alias", sa.String(256), nullable=False), sa.Column("alias_type", sa.String(32), nullable=False), sa.Column("source", sa.String(64), nullable=False), sa.Column("priority", sa.Integer, nullable=False), sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False), sa.Column("valid_to", sa.DateTime(timezone=True)), sa.Column("is_active", sa.Boolean, nullable=False), sa.UniqueConstraint("entity_type", "entity_id", "normalized_alias", "valid_from"))
    op.create_index("ix_entity_alias_lookup", "external_entity_aliases", ["entity_type", "normalized_alias", "is_active"])
def downgrade():
    op.drop_index("ix_entity_alias_lookup", table_name="external_entity_aliases"); op.drop_table("external_entity_aliases")
