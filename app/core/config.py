# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

# app/core/config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Or "allow", NOT "forbid"
    )
    
    # Core app
    APP_ENV: Literal["dev", "prod"] = "dev"
    DATABASE_URL: str
    
    # Auth
    AUTH_JWT_SECRET_KEY: str
    AUTH_JWT_ALGORITHM: str = "HS256"
    AUTH_JWT_ACCESS_TOKEN_TTL_SECONDS: int = 3600
    
    # Remove AuthSettings class entirely
    # Use: settings.AUTH_JWT_SECRET_KEY

settings = Settings()