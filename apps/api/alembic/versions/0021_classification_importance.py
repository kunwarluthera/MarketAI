"""Layer 2.4 persisted impact and importance lineage."""
from alembic import op
import sqlalchemy as sa
revision = "0021_classification_importance"
down_revision = "0020_external_relations"
def upgrade():
    op.add_column("external_classifications", sa.Column("importance_level", sa.String(16), nullable=False, server_default="low"))
    op.add_column("external_classifications", sa.Column("importance_signals", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")))
def downgrade():
    op.drop_column("external_classifications", "importance_signals"); op.drop_column("external_classifications", "importance_level")
