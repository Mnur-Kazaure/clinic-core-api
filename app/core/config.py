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




# # app/core/config.py

# from pydantic_settings import BaseSettings


# class Settings(BaseSettings):
#     """
#     Application configuration.

#     Values can be overridden via environment variables.
#     """

#     # 🔐 Security / Auth
#     JWT_SECRET_KEY: str = "dev-secret-key"
#     JWT_ALGORITHM: str = "HS256"

#     # 🌍 App
#     APP_NAME: str = "Clinic MVP"
#     ENVIRONMENT: str = "development"

#     class Config:
#         env_file = ".env"
#         env_file_encoding = "utf-8"


# # Singleton settings instance
# settings = Settings()