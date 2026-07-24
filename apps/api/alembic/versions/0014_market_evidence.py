"""Layer 2.3 deterministic evidence store."""
from alembic import op
import sqlalchemy as sa
revision = "0014_market_evidence"
down_revision = "0013_feature_values"
def upgrade():
    bind = op.get_bind()
    bind.exec_driver_sql("""CREATE TABLE IF NOT EXISTS evidence_evaluations (
      id VARCHAR(36) PRIMARY KEY, instrument_id VARCHAR(36) NOT NULL, interval VARCHAR(8) NOT NULL,
      evaluation_time TIMESTAMPTZ NOT NULL, evidence_code VARCHAR(64) NOT NULL, rule_version VARCHAR(16) NOT NULL,
      category VARCHAR(32) NOT NULL, direction VARCHAR(16) NOT NULL, state VARCHAR(32) NOT NULL,
      strength NUMERIC(8,6) NOT NULL, expires_at TIMESTAMPTZ NOT NULL, readiness VARCHAR(16) NOT NULL,
      inputs JSON NOT NULL, lineage JSON NOT NULL, created_at TIMESTAMPTZ NOT NULL,
      UNIQUE (instrument_id, interval, evaluation_time, evidence_code, rule_version))""")
    bind.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_evidence_lookup ON evidence_evaluations (instrument_id, interval, evaluation_time, evidence_code)")
def downgrade():
    op.drop_index("ix_evidence_lookup", table_name="evidence_evaluations")
    op.drop_table("evidence_evaluations")
