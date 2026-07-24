"""Layer 2.2 deterministic feature store."""
from alembic import op
import sqlalchemy as sa

revision = "0013_feature_values"
down_revision = "0012_intel_authority_index"


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""CREATE TABLE IF NOT EXISTS feature_values (
        id VARCHAR(36) PRIMARY KEY, instrument_id VARCHAR(36) NOT NULL, interval VARCHAR(8) NOT NULL,
        observed_at TIMESTAMPTZ NOT NULL, feature_name VARCHAR(64) NOT NULL, feature_version VARCHAR(16) NOT NULL,
        value NUMERIC(24,10), calculation_version VARCHAR(32) NOT NULL, source_started_at TIMESTAMPTZ,
        source_ended_at TIMESTAMPTZ, calculated_at TIMESTAMPTZ NOT NULL, lineage JSON NOT NULL,
        UNIQUE (instrument_id, interval, observed_at, feature_name, feature_version))""")
    op.create_table(
        "feature_values_unused_guard",
        "feature_values",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("instrument_id", sa.String(36), nullable=False),
        sa.Column("interval", sa.String(8), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_name", sa.String(64), nullable=False),
        sa.Column("feature_version", sa.String(16), nullable=False),
        sa.Column("value", sa.Numeric(24, 10)),
        sa.Column("calculation_version", sa.String(32), nullable=False),
        sa.Column("source_started_at", sa.DateTime(timezone=True)),
        sa.Column("source_ended_at", sa.DateTime(timezone=True)),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lineage", sa.JSON, nullable=False),
        sa.UniqueConstraint("instrument_id", "interval", "observed_at", "feature_name", "feature_version"),
    )
    op.drop_table("feature_values_unused_guard")
    bind.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_feature_values_lookup ON feature_values (instrument_id, interval, observed_at, feature_name)")


def downgrade() -> None:
    op.drop_index("ix_feature_values_lookup", table_name="feature_values")
    op.drop_table("feature_values")
