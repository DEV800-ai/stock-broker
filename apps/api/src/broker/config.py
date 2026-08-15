from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:password@localhost:5432/signalalpha"

    api_key: str = ""

    # Second, distinct secret for human-confirmation-gated actions (order/paper-trade
    # approval, kill switch). See auth.py::require_human_actor. Optional: if unset
    # (default), those endpoints fall back to accepting api_key alone, so existing
    # single-key deployments keep working unchanged. Set this once a caller other than
    # the frontend (e.g. a future agent gateway) holds api_key, so that caller can't
    # also approve trades or touch the kill switch.
    human_approval_key: str = ""

    ibkr_gateway_url: str = "https://localhost:5000"
    ibkr_account_id: str = ""

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

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

    # Phase 4 gate — see execution/ibkr_adapter.py. Inert today: no code path
    # reads this to enable live execution yet.
    enable_live_trading: bool = False

    # portfolio/ibkr_provider.py::PortfolioSnapshot.is_stale() threshold. Inert
    # today: nothing calls IBKRPortfolioProvider from a live request path yet.
    ibkr_portfolio_max_staleness_seconds: int = 300


settings = Settings()
