"""Layer 3.6.5D explainability governance lifecycle."""
from alembic import op
import sqlalchemy as sa
revision = "0057_explainability_governance"
down_revision = "0056_global_explainability"
def upgrade():
    op.create_table("ml_explainability_governance", sa.Column("id", sa.String(36), primary_key=True), sa.Column("artifact_id", sa.String(64), unique=True), sa.Column("status", sa.String(24)), sa.Column("payload", sa.JSON), sa.Column("checksum", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.create_table("ml_explainability_governance_records", sa.Column("id", sa.String(36), primary_key=True), sa.Column("artifact_id", sa.String(64)), sa.Column("record_type", sa.String(32)), sa.Column("payload", sa.JSON), sa.Column("checksum", sa.String(64), unique=True), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
def downgrade():
    op.drop_table("ml_explainability_governance_records")
    op.drop_table("ml_explainability_governance")
