"""Application configuration via pydantic-settings.

All values are read from environment variables (12-factor).
See infra/docker/.env.example for the full list.
"""

from pydantic import AliasChoices, Field, field_validator, model_validator
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
    APP_VERSION: str = "0.0.1"
    DEBUG: bool = False
    SECRET_KEY: str = Field(
        default="CHANGE_ME_IN_PRODUCTION_MIN_32_BYTES_RANDOM",
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET"),
    )

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
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # SMTP (for email verification — Issue #39)
    # In dev: MailPit catches all mail at smtp://mailpit:1025 (UI on :8025)
    # In prod: configure a real SMTP relay
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@moodsync.local"
    SMTP_USE_TLS: bool = True  # STARTTLS — disable for MailPit/MailHog dev relays
    SMTP_TIMEOUT: int = 10  # seconds

    # Email verification (ADR-0004: 24h TTL)
    EMAIL_VERIFICATION_TTL_HOURS: int = 24
    # Public base URL used to build the verify link in outgoing mails.
    # Frontend route handles the GET and calls the API.
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        if isinstance(v, list):
            return [str(origin).strip() for origin in v]
        raise TypeError("CORS_ORIGINS must be a comma-separated string or list")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.APP_ENV.lower() in {"production", "staging"} and (
            self.SECRET_KEY.startswith("CHANGE_ME") or len(self.SECRET_KEY) < 32
        ):
            raise ValueError(
                "SECRET_KEY must be set to at least 32 random characters in production"
            )
        return self


settings = Settings()
