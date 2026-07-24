"""Layer 3.5.4 immutable promotion governance records."""

from alembic import op
import sqlalchemy as sa

revision = "0034_promotion_requests"
down_revision = "0033_model_candidates"


def upgrade():
    op.create_table(
        "promotion_request_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("candidate_identity", sa.String(64), nullable=False),
        sa.Column("stage", sa.String(40), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("lineage", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("promotion_request_records")
