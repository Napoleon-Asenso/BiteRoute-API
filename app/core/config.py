"""Application configuration management using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings and environment variable bindings."""

    API_TITLE: str = Field(default="BiteRoute API", description="Public application title")
    API_VERSION: str = Field(default="v1", description="Application API version identifier")
    API_V1_PREFIX: str = Field(default="/api/v1", description="Prefix for version 1 API endpoints")
    DEBUG: bool = Field(default=False, description="Debug mode flag")

    # Rate limiting parameters
    RATE_LIMIT: str = Field(
        default="100/minute",
        description="Human-readable rate limit setting string",
    )
    RATE_LIMIT_REQUESTS: int = Field(
        default=100,
        description="Maximum requests allowed per window per client IP",
    )
    RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=60,
        description="Duration of rate limit window in seconds",
    )
    RATE_LIMIT_INACTIVE_TTL_SECONDS: int = Field(
        default=120,
        description="TTL for purging inactive client IP records from memory",
    )

    # Database connection string (default SQLite for instant local dev, overridden via .env)
    DATABASE_URL: str = Field(
        default="sqlite:///./biteroute.db",
        description="SQLAlchemy database connection URI",
    )

    # Pagination bounds
    DEFAULT_LIMIT: int = Field(default=20, description="Default pagination limit")
    MAX_LIMIT: int = Field(default=100, description="Maximum permitted pagination limit")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
