from decimal import Decimal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "local"
    demo_mode: bool = True
    trading_mode: str = "PAPER"
    live_trading_enabled: bool = False
    database_url: str = "sqlite:///./market_ai.db"
    test_database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    app_timezone: str = "Asia/Kolkata"
    demo_username: str = "demo"
    demo_password: str = "papertrade"
    jwt_secret: str = "local-demo-secret-change-me"
    max_risk_per_trade_percent: Decimal = Decimal("0.5")
    max_capital_per_trade_percent: Decimal = Decimal("10")
    max_daily_loss_percent: Decimal = Decimal("2")
    max_open_positions: int = 5
    max_portfolio_exposure_percent: Decimal = Decimal("50")
    max_sector_exposure_percent: Decimal = Decimal("25")
    min_risk_reward: Decimal = Decimal("1.5")
    eod_exit_enabled: bool = True
    eod_exit_time_ist: str = "15:20"
    ledger_rounding_tolerance_inr: Decimal = Decimal("0.05")
    ledger_critical_mismatch_inr: Decimal = Decimal("1.00")


settings = Settings()
