"""Layer 2.4 deterministic external intelligence raw and normalized stores."""
from alembic import op
import sqlalchemy as sa
revision = "0015_external_intelligence"
down_revision = "0014_market_evidence"
def upgrade():
    op.create_table("external_raw_items", sa.Column("id", sa.String(36), primary_key=True), sa.Column("provider", sa.String(32), nullable=False), sa.Column("provider_item_id", sa.String(256)), sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False), sa.Column("payload_checksum", sa.String(64), nullable=False), sa.Column("raw_payload", sa.JSON, nullable=False), sa.Column("processing_status", sa.String(24), nullable=False), sa.UniqueConstraint("provider", "provider_item_id", "payload_checksum"))
    op.create_table("external_items", sa.Column("id", sa.String(36), primary_key=True), sa.Column("canonical_identity", sa.String(64), nullable=False, unique=True), sa.Column("provider", sa.String(32), nullable=False), sa.Column("title", sa.String(512), nullable=False), sa.Column("normalized_title", sa.String(512), nullable=False), sa.Column("canonical_url", sa.String(2048), nullable=False), sa.Column("published_at", sa.DateTime(timezone=True), nullable=False), sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False), sa.Column("content_hash", sa.String(64)), sa.Column("processing_version", sa.String(16), nullable=False), sa.Column("raw_item_id", sa.String(36), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("external_duplicate_links", sa.Column("id", sa.String(36), primary_key=True), sa.Column("canonical_item_id", sa.String(36), nullable=False), sa.Column("duplicate_item_id", sa.String(36), nullable=False), sa.Column("relationship_type", sa.String(32), nullable=False), sa.Column("similarity_score", sa.Numeric(8,6), nullable=False), sa.Column("rule_version", sa.String(16), nullable=False), sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False))
def downgrade():
    op.drop_table("external_duplicate_links"); op.drop_table("external_items"); op.drop_table("external_raw_items")
