from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    JWT_SECRET_KEY: str = "dev-secret-change-later"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_TTL_SECONDS: int = 60 * 60  # 1 hour

    class Config:
        env_prefix = "AUTH_"


auth_settings = AuthSettings()