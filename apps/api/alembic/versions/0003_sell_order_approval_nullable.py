"""Allow independently authorised SELL exit orders."""
from alembic import op

revision = "0003_sell_order_approval"
down_revision = "0002_durable_core"


def upgrade() -> None:
    op.alter_column("orders", "approval_id", nullable=True)


def downgrade() -> None:
    op.alter_column("orders", "approval_id", nullable=False)
