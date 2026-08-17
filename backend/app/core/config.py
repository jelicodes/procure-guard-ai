from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Procure Guard AI"
    database_url: str = "sqlite:///./procure_guard.db"
    groq_api_key: str | None = None
    google_api_key: str | None = None
    erp_mcp_url: str = "http://mcp-server:8001/mcp"
    erp_mcp_transport: str = "http"
    approval_threshold: float = 50_000_000.0
    scan_interval_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()