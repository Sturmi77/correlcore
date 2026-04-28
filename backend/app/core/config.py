"""Application configuration via pydantic-settings.

All values are read from environment variables (12-factor).
See infra/docker/.env.example for the full list.
"""

from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_ENV: str = "development"  # development | staging | production
    DEBUG: bool = False
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_MIN_32_BYTES_RANDOM"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://moodsync:moodsync@localhost:5432/moodsync"

    # Redis
    REDIS_URL: str = "redis://:changeme@localhost:6379/0"

    # JWT (ADR-0004: Phase 1 native JWT)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Encryption at-rest (ADR-0005)
    # Must be a 32-byte URL-safe base64 string. Keep separate from DB backup!
    ENCRYPTION_KEY: str = "CHANGE_ME_32_BYTE_BASE64_KEY_HERE"

    # MinIO / S3
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "moodsync"
    MINIO_SECRET_KEY: str = "CHANGE_ME_MINIO_SECRET"
    MINIO_BUCKET_PHOTOS: str = "moodsync-photos"
    MINIO_SECURE: bool = False  # True in production behind Traefik TLS

    # CORS — list of allowed frontend origins
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # SMTP (for email verification)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@moodsync.local"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v  # type: ignore[return-value]


settings = Settings()
