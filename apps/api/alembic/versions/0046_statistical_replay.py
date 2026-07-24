"""Persist deterministic statistical validation replay comparisons."""
from alembic import op
import sqlalchemy as sa

revision = "0046_statistical_replay"
down_revision = "0045_reference_distribution"


def upgrade():
    op.create_table(
        "ml_statistical_validation_replays",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("replay_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("request_identity", sa.String(64), nullable=False),
        sa.Column("manifest_identity", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("mismatches", sa.JSON, nullable=False),
        sa.Column("replay_checksum", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        if_not_exists=True,
    )
    op.create_index("ix_ml_statistical_validation_replays_request_identity", "ml_statistical_validation_replays", ["request_identity"], if_not_exists=True)
    op.create_index("ix_ml_statistical_validation_replays_manifest_identity", "ml_statistical_validation_replays", ["manifest_identity"], if_not_exists=True)


def downgrade():
    op.drop_table("ml_statistical_validation_replays")
