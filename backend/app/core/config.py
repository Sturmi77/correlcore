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
    DEV_VIEW_ENABLED: bool = False
    DEV_DB_BACKUP_DIR: str = "/tmp/correlcore-backups"
    IMAGE_TAG: str = "latest"
    IMAGE_DIGEST: str = ""
    GIT_COMMIT: str = "unknown"
    GIT_BRANCH: str = "unknown"
    BUILD_TIME: str = ""
    SECRET_KEY: str = Field(
        default="CHANGE_ME_IN_PRODUCTION_MIN_32_BYTES_RANDOM",
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET"),
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://correlcore:correlcore@localhost:5432/correlcore"

    # Redis
    REDIS_URL: str = "redis://:changeme@localhost:6379/0"

    # Rate limiting
    RATE_LIMIT_STORAGE_URL: str = ""
    RATE_LIMIT_TRUST_PROXY_HEADERS: bool = False

    # JWT (ADR-0004: Phase 1 native JWT)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Auth-Cookie Secure-Flag (ADR-0006).
    # ADR-0006 schreibt `Secure` in Produktion vor; Cookies mit `Secure`
    # werden vom Browser bei HTTP-Origins (z. B. lokales Tailscale-Setup
    # ohne TLS) verworfen, was Login/Refresh stillschweigend bricht. Auto-
    # Heuristik: ``None`` (Default) -> True ausser im APP_ENV=development.
    # Für HTTP-Staging-/Homelab-Setups kann der Operator explizit
    # ``COOKIE_SECURE=false`` setzen; in Production weigert sich der
    # Validator, Secure auszuschalten (siehe model_validator unten).
    COOKIE_SECURE: bool | None = None

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
    MINIO_ACCESS_KEY: str = "correlcore"
    MINIO_SECRET_KEY: str = "CHANGE_ME_MINIO_SECRET"
    MINIO_BUCKET_PHOTOS: str = "correlcore-photos"
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
    SMTP_FROM: str = "noreply@correlcore.local"
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
    # Password reset (O-20: shorter TTL than verification)
    PASSWORD_RESET_TTL_HOURS: int = 1
    # Storage limitation (DSGVO Art. 5(1)(e)): unverified accounts that
    # never click the mail link are hard-deleted by the worker after this
    # many days so email addresses do not remain blocked forever.
    UNVERIFIED_CLEANUP_DAYS: int = Field(default=7, ge=1)
    # Sync conflict log retention (ADR-0003 / ADR-0036 §7).
    SYNC_CONFLICT_RETENTION_DAYS: int = Field(default=90, ge=1)
    # Initial pull window when ``since`` cursor is omitted (ADR-0036 §3).
    SYNC_INITIAL_PULL_DAYS: int = Field(default=30, ge=1)
    # Minimum pairwise usage count before a tag can produce a tag->mood insight.
    # This is intentionally stricter than the global entry-count tier because
    # rare tags have too little statistical power even inside a large history.
    ANALYTICS_MIN_TAG_USAGES: int = Field(default=10, ge=2)

    # Comma-separated admin emails allowed to call POST /insights/trigger.
    INSIGHT_TRIGGER_ADMIN_EMAILS: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("INSIGHT_TRIGGER_ADMIN_EMAILS", mode="before")
    @classmethod
    def parse_insight_trigger_admin_emails(cls, v: object) -> list[str]:
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [email.strip().casefold() for email in v.split(",") if email.strip()]
        if isinstance(v, list):
            return [str(email).strip().casefold() for email in v if str(email).strip()]
        raise TypeError("INSIGHT_TRIGGER_ADMIN_EMAILS must be a comma-separated string or list")

    # Notes in analysis — minimum signal confidence for insight evidence (ADR-N-02).
    NOTE_SIGNAL_MIN_CONFIDENCE: float = Field(default=0.70, ge=0.0, le=1.0)

    # Error tracking (M9) — optional selfhosted GlitchTip via Sentry protocol.
    # Leave empty for zero outbound error-reporting traffic.
    GLITCHTIP_DSN: str = ""
    GLITCHTIP_ENVIRONMENT: str = ""
    GLITCHTIP_TRACES_SAMPLE_RATE: float = Field(default=0.0, ge=0.0, le=1.0)

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

    @property
    def cookie_secure_effective(self) -> bool:
        """Effective Secure-Flag for auth cookies (ADR-0006).

        - Wenn ``COOKIE_SECURE`` explizit ``True``/``False`` gesetzt ist, gilt
          das (mit Production-Sicherheits-Override im Validator).
        - Wenn ``None`` (Default), schalten wir ``Secure`` nur in
          ``APP_ENV=development`` aus; alle anderen Umgebungen (staging,
          production) starten mit ``Secure=True``. Operatoren von HTTP-only
          Staging-/Homelab-Setups (z. B. Tailscale-IP ohne TLS) müssen
          dann explizit ``COOKIE_SECURE=false`` setzen — andernfalls
          verwirft der Browser ``Set-Cookie`` und Login schlägt fehl.
        """
        if self.COOKIE_SECURE is not None:
            return self.COOKIE_SECURE
        return self.APP_ENV.lower() != "development"

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
        # ADR-0006: Secure ist in Produktion nicht abschaltbar. Staging darf
        # COOKIE_SECURE=false setzen (Homelab-HTTP-Setups), Production nicht.
        if self.APP_ENV.lower() == "production" and self.COOKIE_SECURE is False:
            raise ValueError(
                "COOKIE_SECURE=false ist in APP_ENV=production nicht erlaubt "
                "(ADR-0006: Secure-Flag verbindlich). Bitte HTTPS terminieren "
                "(z. B. Reverse-Proxy mit TLS) und COOKIE_SECURE entfernen "
                "oder auf true setzen."
            )
        return self


settings = Settings()
