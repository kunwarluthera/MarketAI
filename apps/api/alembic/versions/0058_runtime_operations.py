"""Layer 3.6.6 runtime operations governance."""
from alembic import op
import sqlalchemy as sa
revision = "0058_runtime_operations"
down_revision = "0057_explainability_governance"
def upgrade():
    op.create_table("ml_runtime_operation_policies", sa.Column("id", sa.String(36), primary_key=True), sa.Column("policy_code", sa.String(100), unique=True), sa.Column("enabled", sa.Boolean), sa.Column("payload", sa.JSON), sa.Column("checksum", sa.String(64)), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    for table, columns in {"ml_runtime_health_snapshots": [("snapshot_checksum", sa.String(64), True), ("payload", sa.JSON, False)], "ml_runtime_services": [("service_name", sa.String(80), False), ("status", sa.String(24), False), ("payload", sa.JSON, False)], "ml_runtime_incidents": [("incident_id", sa.String(64), True), ("severity", sa.String(16), False), ("status", sa.String(24), False), ("payload", sa.JSON, False)], "ml_runtime_reports": [("report_checksum", sa.String(64), True), ("payload", sa.JSON, False)]}.items():
        op.create_table(table, sa.Column("id", sa.String(36), primary_key=True), *(sa.Column(name, typ, unique=unique) for name, typ, unique in columns), sa.Column("created_at", sa.DateTime(timezone=True)), if_not_exists=True)
    op.execute(sa.text("INSERT INTO ml_runtime_operation_policies (id, policy_code, enabled, payload, checksum, created_at) VALUES ('runtime-policy-v1', 'CONTROLLED_RUNTIME_OPERATIONS_V1', true, '{}', 'seeded-runtime-v1', CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"))
def downgrade():
    for table in ("ml_runtime_reports", "ml_runtime_incidents", "ml_runtime_services", "ml_runtime_health_snapshots", "ml_runtime_operation_policies"):
        op.drop_table(table)
