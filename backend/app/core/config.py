"""Application configuration via pydantic-settings.

All values are read from environment variables (12-factor).
See infra/docker/.env.example for the full list.
"""

from typing import Annotated

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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

    # Encryption at-rest (ADR-0005, Issue #26)
    # Master-Key wraps per-user DEKs in user_encryption_keys.wrapped_dek.
    # During key rotation: ENCRYPTION_KEYS as comma-separated list, new key first.
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = "CHANGE_ME_32_BYTE_BASE64_KEY_HERE"
    # NoDecode keeps pydantic-settings from JSON-parsing the ENV value;
    # the field_validator below splits comma-separated strings.
    ENCRYPTION_KEYS: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        description="Optional comma-separated list of master keys, used during rotation. "
        "If empty, ENCRYPTION_KEY is used. First entry encrypts new data; "
        "all entries can decrypt existing data.",
    )

    # MinIO / S3
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "moodsync"
    MINIO_SECRET_KEY: str = "CHANGE_ME_MINIO_SECRET"
    MINIO_BUCKET_PHOTOS: str = "moodsync-photos"
    MINIO_SECURE: bool = False  # True in production behind Traefik TLS

    # CORS — list of allowed frontend origins.
    # NoDecode prevents pydantic-settings from JSON-parsing the ENV value;
    # the field_validator below handles comma-separated strings instead.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # SMTP (for email verification — Issue #39)
    # In dev: MailPit catches all mail at smtp://mailpit:1025 (UI on :8025)
    # In prod: configure a real SMTP relay
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@moodsync.local"
    # STARTTLS-Default ist `None` (= Auto): TLS an, sobald `SMTP_USER` gesetzt
    # ist (echter Relay), aus, wenn keine Auth konfiguriert ist (Mailpit/MailHog
    # im Homelab sprechen Plain-SMTP auf 1025 ohne STARTTLS-Support). Override
    # via `SMTP_USE_TLS=true` / `false` in der `.env` jederzeit möglich.
    SMTP_USE_TLS: bool | None = None
    SMTP_TIMEOUT: int = 10  # seconds

    @property
    def smtp_should_use_tls(self) -> bool:
        """Effective STARTTLS-Setting: explicit override wins, sonst auto.

        - Wenn ``SMTP_USE_TLS`` explizit ``True``/``False`` gesetzt ist, gilt das.
        - Wenn ``SMTP_USE_TLS`` ``None`` ist (Default), schalten wir TLS nur ein,
          wenn ``SMTP_USER`` einen nicht-leeren Wert hat — die Heuristik
          "Auth = echter Relay = STARTTLS, keine Auth = Dev-Catcher = plain".
        """
        if self.SMTP_USE_TLS is not None:
            return self.SMTP_USE_TLS
        return bool(self.SMTP_USER)

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

    @field_validator("ENCRYPTION_KEYS", mode="before")
    @classmethod
    def parse_encryption_keys(cls, v: object) -> list[str]:
        """Accept comma-separated string or list. Empty -> []. Whitespace stripped."""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        if isinstance(v, list):
            return [str(k).strip() for k in v if str(k).strip()]
        raise TypeError("ENCRYPTION_KEYS must be a comma-separated string or list")

    def effective_encryption_keys(self) -> list[str]:
        """Return the master-key list to use for crypto operations.

        Precedence: ENCRYPTION_KEYS list > ENCRYPTION_KEY scalar.
        Always returns at least one key (never empty); raises if neither set.
        The first key is used for new encryptions; all are used for decryption.
        """
        if self.ENCRYPTION_KEYS:
            return self.ENCRYPTION_KEYS
        return [self.ENCRYPTION_KEY]

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.APP_ENV.lower() in {"production", "staging"}:
            if self.SECRET_KEY.startswith("CHANGE_ME") or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be set to at least 32 random characters in production"
                )
            keys = self.effective_encryption_keys()
            if any(k.startswith("CHANGE_ME") for k in keys):
                raise ValueError(
                    "ENCRYPTION_KEY (or ENCRYPTION_KEYS) must be set to a real "
                    "Fernet key in production. Generate with: "
                    "python -c 'from cryptography.fernet import Fernet; "
                    "print(Fernet.generate_key().decode())'"
                )
        return self


settings = Settings()
