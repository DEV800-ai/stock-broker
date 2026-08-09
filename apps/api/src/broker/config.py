from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:password@localhost:5432/signalalpha"

    api_key: str = ""

    ibkr_gateway_url: str = "https://localhost:5000"
    ibkr_account_id: str = ""

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    finnhub_api_key: str = ""

    scanner_min_score: float = 0.30
    thesis_min_score: float = 0.50
    scanner_universe_size: int = 500

    paper_account_equity: float = 100_000.0
    risk_cooldown_days: int = 14
    order_preview_ttl_minutes: int = 5

    # Paper fill simulation — see execution/paper_adapter.py
    paper_fill_slippage_bps: float = 5.0
    paper_fill_partial_adv_pct: float = 0.10
    paper_fill_reject_adv_pct: float = 0.25
    paper_fill_min_partial_ratio: float = 0.3


settings = Settings()
