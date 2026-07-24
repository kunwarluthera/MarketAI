"""Layer 3.5.3 immutable candidate registrations."""

from alembic import op
import sqlalchemy as sa

revision = "0033_model_candidates"
down_revision = "0032_model_versions"


def upgrade():
    op.create_table(
        "model_candidate_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("version_identity", sa.String(64), nullable=False),
        sa.Column("registration_identity", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("lineage", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("version_identity"),
    )


def downgrade():
    op.drop_table("model_candidate_records")
