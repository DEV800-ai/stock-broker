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

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    finnhub_api_key: str = ""

    # SEC requires a descriptive User-Agent identifying the requester on all
    # data.sec.gov / sec.gov calls, e.g. "SignalAlpha you@example.com". Unset
    # skips EDGAR filing fetches (see data/edgar.py), same degrade-gracefully
    # pattern as finnhub_api_key.
    sec_edgar_user_agent: str = ""

    scanner_min_score: float = 0.30
    thesis_min_score: float = 0.50
    thesis_recheck_max_age_hours: int = 24
    # Holding horizon the thesis agent is told to calibrate its reasoning and
    # confidence to — this app is paper-trading/swing-oriented, not day-trading.
    thesis_target_horizon: str = "1-3 months"
    scanner_universe_size: int = 500
    # A scan can legitimately run 60-90+ min for the full universe. Only let
    # delete_scan_run clear a still-"running" run once it's been running
    # longer than this — otherwise it races the background scan task and
    # crashes it with ObjectDeletedError mid-scan.
    scan_stale_after_minutes: int = 120

    paper_account_equity: float = 100_000.0
    risk_cooldown_days: int = 14
    order_preview_ttl_minutes: int = 5

    # Paper fill simulation — see execution/paper_adapter.py
    paper_fill_slippage_bps: float = 5.0
    paper_fill_partial_adv_pct: float = 0.10
    paper_fill_reject_adv_pct: float = 0.25
    paper_fill_min_partial_ratio: float = 0.3

settings = Settings()
