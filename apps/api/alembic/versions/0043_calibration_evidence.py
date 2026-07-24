"""Layer 3.6.3B immutable historical calibration evidence."""
from alembic import op
import sqlalchemy as sa

revision = "0043_calibration_evidence"
down_revision = "0042_statistical_lifecycle"


def upgrade():
    op.create_table("ml_calibration_evidence", sa.Column("id", sa.String(36), primary_key=True), sa.Column("evidence_identity", sa.String(64), nullable=False, unique=True), sa.Column("model_version_identity", sa.String(64), nullable=False), sa.Column("output_contract_identity", sa.String(64), nullable=False), sa.Column("validation_dataset_identity", sa.String(64), nullable=False), sa.Column("task_type", sa.String(32), nullable=False), sa.Column("sample_count", sa.Integer, nullable=False), sa.Column("expected_calibration_error", sa.Float, nullable=False), sa.Column("maximum_calibration_error", sa.Float, nullable=True), sa.Column("brier_score", sa.Float, nullable=True), sa.Column("log_loss", sa.Float, nullable=True), sa.Column("status", sa.String(32), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("evidence_checksum", sa.String(64), nullable=False), sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)


def downgrade():
    op.drop_table("ml_calibration_evidence")
