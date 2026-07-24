"""Layer 3.6.3B calibration evidence validity governance."""
from alembic import op
import sqlalchemy as sa

revision = "0047_calibration_governance"
down_revision = "0046_statistical_replay"


def upgrade():
    op.execute(sa.text("ALTER TABLE ml_calibration_evidence ADD COLUMN IF NOT EXISTS valid_from TIMESTAMP WITH TIME ZONE"))
    op.execute(sa.text("ALTER TABLE ml_calibration_evidence ADD COLUMN IF NOT EXISTS valid_to TIMESTAMP WITH TIME ZONE"))
    op.execute(sa.text("ALTER TABLE ml_calibration_evidence ADD COLUMN IF NOT EXISTS approved_by VARCHAR(120)"))


def downgrade():
    op.drop_column("ml_calibration_evidence", "approved_by")
    op.drop_column("ml_calibration_evidence", "valid_to")
    op.drop_column("ml_calibration_evidence", "valid_from")
