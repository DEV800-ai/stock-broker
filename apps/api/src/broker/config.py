from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:password@localhost:5432/signalalpha"

    ibkr_gateway_url: str = "http://localhost:5000"
    ibkr_account_id: str = ""

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    finnhub_api_key: str = ""

    scanner_min_score: float = 0.30
    thesis_min_score: float = 0.50
    scanner_universe_size: int = 500


settings = Settings()
