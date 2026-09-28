"""Platform-X application configuration.

Loads settings from environment variables with sensible defaults
for local development. Includes production hardening validators.
"""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET = "dev-secret-key-change-in-production"


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Platform-X"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = True
    APP_VERSION: str = "0.1.0"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite:///./platform_x.db"

    # Security
    SECRET_KEY: str = _DEV_SECRET
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days
    ALGORITHM: str = "HS256"
    BCRYPT_ROUNDS: int = 12

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    # Multi-tenancy
    DEFAULT_TENANT_SLUG: str = "demo"

    # Email (Resend)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "onboarding@resend.dev"
    EMAIL_FROM_NAME: str = "Platform-X"
    EMAIL_ENABLED: bool = False

    # SMS (Twilio — Phase 11 later)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    SMS_ENABLED: bool = False

    # AI
    AI_PROVIDER: str = "mock"  # mock | gemini | openai
    AI_ENABLED: bool = True
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AI_MAX_TOKENS_PER_MESSAGE: int = 1024
    AI_RATE_LIMIT_PER_MINUTE: int = 20

    # Feature flags
    ENABLE_MOCK_PAYMENTS: bool = True

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> "Settings":
        """Fail fast if production is configured unsafely."""
        if self.APP_ENV == "production":
            if self.SECRET_KEY == _DEV_SECRET or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be set to a strong value (>=32 chars) in production"
                )
            if self.APP_DEBUG:
                raise ValueError("APP_DEBUG must be False in production")
            if self.ENABLE_MOCK_PAYMENTS:
                raise ValueError("ENABLE_MOCK_PAYMENTS must be False in production")
            if any("localhost" in origin or "127.0.0.1" in origin for origin in self.CORS_ORIGINS):
                raise ValueError("CORS_ORIGINS must not contain localhost in production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
