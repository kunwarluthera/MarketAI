from __future__ import annotations
from datetime import UTC, datetime
from app.common.models import SystemSetting

DEFAULTS = {
    "max_risk_per_trade_percent": "0.5",
    "max_capital_per_trade_percent": "10",
    "max_daily_realised_loss_percent": "2",
    "max_daily_total_loss_percent": "2",
    "max_open_positions": 5,
    "max_portfolio_exposure_percent": "50",
    "max_sector_exposure_percent": "25",
    "min_risk_reward": "1.5",
    "max_atr_percent": "5",
    "min_average_daily_volume": 0,
    "max_bid_ask_spread_percent": "1",
    "max_consecutive_losses": 3,
    "loss_cooldown_minutes": 30,
    "recommendation_validity_minutes": 5,
    "approval_validity_minutes": 5,
    "allow_position_averaging": False,
    "eod_exit_enabled": True,
    "global_kill_switch": False,
    "block_trading_on_critical_reconciliation_failure": True,
    "ledger_rounding_tolerance_inr": "0.05",
    "ledger_critical_mismatch_inr": "1.00",
    "version": 1,
}


def get_config(session):
    row = session.get(SystemSetting, "risk_config")
    return {**DEFAULTS, **(row.value if row else {})}


def update_config(session, values: dict, reason: str, actor: str):
    row = session.get(SystemSetting, "risk_config", with_for_update=True)
    current = get_config(session)
    version = int(current.get("version", 1)) + 1
    payload = {
        **current,
        **values,
        "version": version,
        "effective_from": datetime.now(UTC).isoformat(),
        "changed_by": actor,
        "change_reason": reason,
    }
    if row:
        row.value = payload
        row.version = version
        row.updated_at = datetime.now(UTC)
    else:
        row = SystemSetting(
            key="risk_config",
            value=payload,
            version=version,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(row)
    session.flush()
    return payload
