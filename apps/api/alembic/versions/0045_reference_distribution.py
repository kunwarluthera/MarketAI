"""Layer 3.6.3B immutable output reference support evidence."""
from alembic import op
import sqlalchemy as sa

revision = "0045_reference_distribution"
down_revision = "0044_regression_evidence"


def upgrade():
    op.create_table("ml_reference_distribution_evidence", sa.Column("id", sa.String(36), primary_key=True), sa.Column("evidence_identity", sa.String(64), nullable=False, unique=True), sa.Column("model_version_identity", sa.String(64), nullable=False), sa.Column("output_contract_identity", sa.String(64), nullable=False), sa.Column("validation_dataset_identity", sa.String(64), nullable=False), sa.Column("task_type", sa.String(32), nullable=False), sa.Column("lower_bound", sa.Float, nullable=False), sa.Column("upper_bound", sa.Float, nullable=False), sa.Column("tolerance", sa.Float, nullable=False), sa.Column("sample_count", sa.Integer, nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("evidence_checksum", sa.String(64), nullable=False), sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)


def downgrade():
    op.drop_table("ml_reference_distribution_evidence")
