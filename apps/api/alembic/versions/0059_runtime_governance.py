"""Layer 3.6.6 SLO, budget, reconciliation and event records."""
from alembic import op
import sqlalchemy as sa
revision = "0059_runtime_governance"
down_revision = "0058_runtime_operations"
def upgrade():
    op.create_table("ml_runtime_operational_records", sa.Column("id", sa.String(36), primary_key=True), sa.Column("record_identity", sa.String(64), unique=True), sa.Column("record_type", sa.String(32)), sa.Column("payload", sa.JSON), sa.Column("checksum", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
def downgrade():
    op.drop_table("ml_runtime_operational_records")
