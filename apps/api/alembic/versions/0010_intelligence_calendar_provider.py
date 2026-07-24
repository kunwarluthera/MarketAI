"""Layer 2.1 calendar and provider health tables."""
from alembic import op
import sqlalchemy as sa

revision = "0010_intel_calendar_provider"
down_revision = "0009_intelligence_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("""CREATE TABLE IF NOT EXISTS intelligence_trading_sessions (
        session_id VARCHAR(32) PRIMARY KEY, session_date TIMESTAMPTZ NOT NULL,
        market_open TIMESTAMPTZ NOT NULL, market_close TIMESTAMPTZ NOT NULL,
        is_holiday BOOLEAN NOT NULL DEFAULT FALSE, is_half_session BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL)""")
    bind.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_intel_sessions_date ON intelligence_trading_sessions (session_date)")
    bind.exec_driver_sql("""CREATE TABLE IF NOT EXISTS intelligence_provider_status (
        provider VARCHAR(64) PRIMARY KEY, last_source_timestamp TIMESTAMPTZ,
        last_received_at TIMESTAMPTZ, freshness_seconds INTEGER,
        status VARCHAR(20) NOT NULL DEFAULT 'unknown', updated_at TIMESTAMPTZ NOT NULL)""")


def downgrade() -> None:
    op.drop_table("intelligence_provider_status")
    op.drop_index("ix_intel_sessions_date", table_name="intelligence_trading_sessions")
    op.drop_table("intelligence_trading_sessions")
