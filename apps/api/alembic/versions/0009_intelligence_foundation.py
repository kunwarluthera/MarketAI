"""Layer 2.1 market intelligence foundation."""
from alembic import op
import sqlalchemy as sa

revision = "0009_intelligence_foundation"
down_revision = "0008_alerts"


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "intelligence_instruments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("exchange", sa.String(32), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("exchange_token", sa.String(128)),
        sa.Column("instrument_type", sa.String(32), nullable=False),
        sa.Column("sector", sa.String(128)),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("metadata_version", sa.Integer, nullable=False),
        sa.Column("metadata_json", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("exchange", "symbol", "valid_from"),
    )
    bind.exec_driver_sql("""
        CREATE TABLE intelligence_candles (
            id VARCHAR(36) NOT NULL,
            instrument_id VARCHAR(36) NOT NULL REFERENCES intelligence_instruments(id),
            interval VARCHAR(8) NOT NULL, source VARCHAR(64) NOT NULL,
            session_id VARCHAR(64), open_price NUMERIC(20,4) NOT NULL,
            high_price NUMERIC(20,4) NOT NULL, low_price NUMERIC(20,4) NOT NULL,
            close_price NUMERIC(20,4) NOT NULL, volume INTEGER NOT NULL,
            trade_count INTEGER NOT NULL, started_at TIMESTAMPTZ NOT NULL,
            ended_at TIMESTAMPTZ NOT NULL, source_timestamp TIMESTAMPTZ NOT NULL,
            received_at TIMESTAMPTZ NOT NULL, freshness_seconds INTEGER NOT NULL,
            is_complete BOOLEAN NOT NULL, revision INTEGER NOT NULL,
            supersedes_id VARCHAR(36), validation_status VARCHAR(20) NOT NULL,
            validation_errors JSON NOT NULL, created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL, PRIMARY KEY (id, started_at),
            CHECK (ended_at > started_at),
            CHECK (open_price > 0 AND high_price > 0 AND low_price > 0 AND close_price > 0),
            CHECK (high_price >= low_price AND high_price >= open_price AND high_price >= close_price),
            CHECK (low_price <= open_price AND low_price <= close_price),
            CHECK (volume >= 0 AND trade_count >= 0),
            UNIQUE (instrument_id, interval, started_at, source)
        ) PARTITION BY RANGE (started_at)
    """)
    for name, start, end in (
        ("intelligence_candles_2026_01", "2026-01-01T00:00:00+00:00", "2026-02-01T00:00:00+00:00"),
        ("intelligence_candles_2026_02", "2026-02-01T00:00:00+00:00", "2026-03-01T00:00:00+00:00"),
        ("intelligence_candles_2026_03", "2026-03-01T00:00:00+00:00", "2026-04-01T00:00:00+00:00"),
    ):
        bind.exec_driver_sql(f"CREATE TABLE {name} PARTITION OF intelligence_candles FOR VALUES FROM ('{start}') TO ('{end}')")
    bind.exec_driver_sql("CREATE TABLE intelligence_candles_default PARTITION OF intelligence_candles DEFAULT")
    bind.exec_driver_sql("CREATE INDEX ix_intel_instruments_symbol ON intelligence_instruments (exchange, symbol)")
    bind.exec_driver_sql("CREATE INDEX ix_intel_candles_lookup ON intelligence_candles (instrument_id, interval, started_at)")


def downgrade() -> None:
    op.drop_index("ix_intel_candles_lookup", table_name="intelligence_candles")
    op.drop_index("ix_intel_instruments_symbol", table_name="intelligence_instruments")
    op.drop_table("intelligence_candles_default")
    op.execute("DROP TABLE intelligence_candles")
    op.drop_table("intelligence_instruments")
