"""Durable PostgreSQL trading core.

Revision ID: 0002_durable_core
Revises: 0001_core
"""

from alembic import op
from app.common.db import Base
from app.common import models  # noqa: F401


revision = "0002_durable_core"
down_revision = "0001_core"


def upgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("audit_logs")
    # Bootstrap the pre-existing Layer 1 core tables only. Intelligence tables
    # are owned exclusively by their Layer 2.1 migrations.
    excluded = {
        "scheduled_jobs",
        "market_snapshots",
        "alerts",
        "risk_rule_results",
        "intelligence_instruments",
        "intelligence_candles",
        "intelligence_trading_sessions",
        "intelligence_provider_status",
        "intelligence_candle_rejections",
        # Layer 2.4 tables are owned by their dedicated migrations (0015+).
        "external_raw_items",
        "external_items",
        "external_duplicate_links",
        "external_entity_aliases",
        "external_entity_mappings",
        "external_classifications",
        "external_intelligence_readiness",
        "external_item_relations",
        "opportunity_records",
        "opportunity_rules",
        "opportunity_discovery_runs",
        "research_snapshots",
        "ml_datasets",
        "ml_label_records",
        "ml_training_runs",
        "metric_aggregation_reports",
        "robustness_reports",
        "validation_decision_records",
        "model_registry_definitions",
        "model_version_records",
        "model_candidate_records",
        "promotion_request_records",
        "model_role_assignments",
        "registry_audit_reports",
        "model_load_manifests",
        "offline_prediction_records",
    }
    Base.metadata.create_all(
        bind=op.get_bind(),
        tables=[t for t in Base.metadata.sorted_tables if t.name not in excluded],
    )


def downgrade() -> None:
    pass
