"""API configuration via pydantic-settings."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    ALLOWED_ORIGIN_REGEX: str = r"https://.*\.vercel\.app"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""  # verifies Supabase-issued JWTs (audience="authenticated")

    # Gemini
    GEMINI_API_KEY: str = ""

    # Internal JWT (fallback when not using Supabase)
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Limits
    MAX_UPLOAD_MB: int = 250

    # Logging
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
