"""Layer 3.6.5A explainability governance and provenance."""
from alembic import op
import sqlalchemy as sa
revision = "0054_explainability"
down_revision = "0053_batch_operations"

def upgrade():
    op.create_table("ml_prediction_explainability_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), unique=True, nullable=False), sa.Column("version", sa.String(24), nullable=False), sa.Column("enabled", sa.Boolean, nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.create_table("ml_prediction_explainability_requests", sa.Column("id", sa.String(36), primary_key=True), sa.Column("explainability_id", sa.String(64), unique=True, nullable=False), sa.Column("prediction_identity", sa.String(64), nullable=False), sa.Column("requested_by", sa.String(128), nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("eligibility", sa.String(32), nullable=False), sa.Column("payload", sa.JSON, nullable=False), sa.Column("checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    for table, cols in {"ml_prediction_provenance": [("explainability_id", "VARCHAR(64) UNIQUE NOT NULL"), ("payload", "JSON NOT NULL"), ("checksum", "VARCHAR(64) NOT NULL")], "ml_prediction_explainability_manifests": [("explainability_id", "VARCHAR(64) UNIQUE NOT NULL"), ("payload", "JSON NOT NULL"), ("checksum", "VARCHAR(64) NOT NULL")], "ml_prediction_explainability_events": [("explainability_id", "VARCHAR(64) NOT NULL"), ("event_identity", "VARCHAR(64) UNIQUE NOT NULL"), ("event_type", "VARCHAR(48) NOT NULL"), ("payload", "JSON NOT NULL")], "ml_prediction_explainability_lineage": [("record_identity", "VARCHAR(64) UNIQUE NOT NULL"), ("record_type", "VARCHAR(24) NOT NULL"), ("source_identity", "VARCHAR(64) NOT NULL"), ("payload", "JSON NOT NULL"), ("checksum", "VARCHAR(64) NOT NULL") ]}.items():
        op.create_table(table, sa.Column("id", sa.String(36), primary_key=True), *(sa.Column(name, sa.Text if typ.startswith("VARCHAR") else sa.JSON, nullable="NOT NULL" in typ, unique="UNIQUE" in typ) for name, typ in cols), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_prediction_explainability_policies (id, policy_code, version, enabled, payload, checksum, created_at) VALUES ('explainability-policy-v1', 'CONTROLLED_EXPLAINABILITY_V1', '1', true, '{}', 'seeded-explainability-v1', CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))

def downgrade():
    for table in ("ml_prediction_explainability_lineage", "ml_prediction_explainability_events", "ml_prediction_explainability_manifests", "ml_prediction_provenance", "ml_prediction_explainability_requests", "ml_prediction_explainability_policies"):
        op.drop_table(table)
