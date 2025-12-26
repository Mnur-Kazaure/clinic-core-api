# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="forbid",
    )

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------
    APP_ENV: Literal["dev", "prod"] = "dev"

    AUTH_MODE: Literal["dev", "jwt"] = "dev"

    DATABASE_URL: str

    # ------------------------------------------------------------------
    # JWT (used only when AUTH_MODE=jwt)
    # ------------------------------------------------------------------
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60


settings = Settings()