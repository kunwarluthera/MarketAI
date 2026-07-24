"""Layer 3.6.3B immutable regression evidence."""
from alembic import op
import sqlalchemy as sa

revision = "0044_regression_evidence"
down_revision = "0043_calibration_evidence"


def upgrade():
    op.create_table("ml_regression_evidence", sa.Column("id", sa.String(36), primary_key=True), sa.Column("evidence_identity", sa.String(64), nullable=False, unique=True), sa.Column("prediction_result_identity", sa.String(64), nullable=False), sa.Column("model_version_identity", sa.String(64), nullable=False), sa.Column("validation_dataset_identity", sa.String(64), nullable=False), sa.Column("predicted_value", sa.Float, nullable=False), sa.Column("residual", sa.Float, nullable=True), sa.Column("interval_lower", sa.Float, nullable=True), sa.Column("interval_upper", sa.Float, nullable=True), sa.Column("uncertainty_width", sa.Float, nullable=True), sa.Column("status", sa.String(32), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("evidence_checksum", sa.String(64), nullable=False), sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)


def downgrade():
    op.drop_table("ml_regression_evidence")
