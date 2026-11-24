from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    vt_api_key: str | None = None
    log_level: str = "INFO"
    env: str = "dev"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash-lite"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dnscope"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    rate_limit_per_minute: int = 60
    api_key_header_name: str = "X-API-Key"
    job_recovery_stale_seconds: int = 60
    api_key_hmac_secret: str = "dev-insecure-hmac-secret-change-in-production"
