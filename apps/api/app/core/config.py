import json
import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Environment
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    # Security
    SECRET_KEY: str = Field(
        default="scratch_development_secret_key_minimum_32_characters_long_for_security"
    )
    CSRF_SECRET: str = Field(
        default="scratch_development_csrf_secret_minimum_32_characters_long_for_security"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # Cookies
    COOKIE_SECURE: bool = Field(default=False)
    COOKIE_SAMESITE: str = Field(default="lax")
    COOKIE_DOMAIN: Optional[str] = Field(default=None)

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://scratch_app:app_local_secret_change_me@localhost:5432/scratch"
    )
    MIGRATOR_DATABASE_URL: Optional[str] = Field(
        default="postgresql+asyncpg://scratch_migrator:migrator_local_secret_change_me@localhost:5432/scratch"
    )
    SYNC_MIGRATOR_DATABASE_URL: Optional[str] = Field(
        default="postgresql://scratch_migrator:migrator_local_secret_change_me@localhost:5432/scratch"
    )

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/1")

    # CORS & Frontend
    FRONTEND_URL: str = Field(default="http://localhost:3000")
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v, info):
        env = info.data.get("ENVIRONMENT", "development")
        if env in ("production", "staging"):
            if len(v) < 32 or "change_me" in v or "insecure" in v:
                raise ValueError(
                    "SECRET_KEY must be a secure, non-default string of at least 32 characters in production"
                )
        return v


settings = Settings()
