"""Application configuration via pydantic-settings.

All values are read from environment variables (12-factor).
See infra/docker/.env.example for the full list.
"""

from typing import Annotated

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# ADR-0006 L1 residual: "no logout denylist" is only acceptable while access
# tokens are short-lived. Cap the TTL in real deployments so an operator cannot
# silently invalidate that assumption (#791).
PROD_MAX_ACCESS_TOKEN_EXPIRE_MINUTES = 15


def _default_app_version() -> str:
    """Single source of truth for the app version: the installed package
    version (``pyproject`` ``[project].version``).

    Keeps the OpenAPI ``info.version`` and the health/instance/Sentry release
    string from drifting off the actual release (audit Q6). Overridable via the
    ``APP_VERSION`` env var; falls back when the distribution metadata is not
    present (e.g. running straight from a source tree without an install).
    """
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("correlcore-backend")
    except PackageNotFoundError:
        return "0.0.0+unknown"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_ENV: str = "development"  # development | staging | production

    @field_validator("APP_ENV", mode="before")
    @classmethod
    def strip_app_env(cls, v: object) -> object:
        """Normalize APP_ENV so whitespace cannot bypass staging/production guards.

        ``validate_production_secrets`` and cookie Secure heuristics compare
        ``APP_ENV.lower()`` to exact tokens. A value like ``\"production \"``
        (trailing space from .env / compose / CI) would otherwise skip secret,
        CORS, DEBUG, and COOKIE_SECURE checks while still looking like production
        to operators.
        """
        if isinstance(v, str):
            return v.strip()
        return v

    APP_VERSION: str = Field(default_factory=_default_app_version)
    DEBUG: bool = False
    DEV_VIEW_ENABLED: bool = False
    DEV_DB_BACKUP_DIR: str = "/tmp/correlcore-backups"

    # Worker freshness monitoring (#756). GET /worker/status exposes age and
    # status of the last successful run per WorkerJobKind so an external
    # uptime monitor (Uptime-Kuma, healthchecks.io, GlitchTip cron monitor)
    # can alert when the nightly worker silently stops making progress —
    # as opposed to crashing loudly, which #745 Phase 4 already covers via
    # GlitchTip error tracking. The endpoint is never fully unauthenticated:
    # it accepts either this static key (for monitors that cannot hold a
    # browser session) or an existing admin user session (`is_admin=True`).
    # Left empty by default; a self-hoster running only Uptime-Kuma/etc.
    # from outside the trusted network should set this explicitly. It is
    # NOT hard-required in production (unlike SECRET_KEY et al.) because the
    # admin-session fallback already keeps the endpoint from being open.
    WORKER_STATUS_API_KEY: str = ""
    # Hours after the last successful daily-cadence run (daily_bundle,
    # insights) before /worker/status reports that job kind as "stale".
    # Jobs run once nightly at 03:00 UTC (see
    # app.workers.analytics.seconds_until_next_cleanup); 30h gives ~6h of
    # slack past the expected ~24h cadence — tighter than the 40h the
    # frontend insight feed uses for its end-user staleness banner (#755),
    # because this value drives ops alerting and should fire before a
    # second nightly run is at risk of being missed too.
    WORKER_STALE_AFTER_HOURS: int = 30
    IMAGE_TAG: str = "latest"
    IMAGE_DIGEST: str = ""
    GIT_COMMIT: str = "unknown"
    GIT_BRANCH: str = "unknown"
    BUILD_TIME: str = ""

    # Deployment descriptor (#734/#735). Exposed via the public
    # ``GET /api/v1/instance`` endpoint so one web bundle can present a
    # self-host CTA or an account-signup CTA at runtime — no rebuild, no
    # build-time flag. ``selfhost`` (default) vs ``hosted`` (managed SaaS,
    # correlcore.com).
    DEPLOYMENT_MODE: str = "selfhost"
    # Whether anonymous visitors may self-register on this instance. Hosted
    # SaaS keeps this open; a locked-down personal selfhost may set it false.
    REGISTRATION_ENABLED: bool = True

    @field_validator("DEPLOYMENT_MODE", mode="before")
    @classmethod
    def normalize_deployment_mode(cls, v: object) -> object:
        """Coerce to the two supported tokens; anything unknown is selfhost."""
        if isinstance(v, str):
            return "hosted" if v.strip().lower() == "hosted" else "selfhost"
        return v

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
    # Escape hatch for isolated CI harnesses that must exercise handler logic
    # without SlowAPI's per-endpoint caps throttling them (e.g. the DAST scan in
    # ci-dast.yml, where every request shares one client IP). MUST stay True in
    # every real deployment; there is no code path that flips it off implicitly.
    RATE_LIMIT_ENABLED: bool = True

    # JWT (ADR-0004: Phase 1 native JWT)
    JWT_ALGORITHM: str = "HS256"
    # ADR-0006 accepts "no logout denylist" as a residual risk *because* access
    # tokens are short-lived (≤15 min): a stolen token expires on its own soon
    # after logout. That guarantee only holds while the TTL stays small, so the
    # value is bounded to PROD_MAX_ACCESS_TOKEN_EXPIRE_MINUTES in
    # staging/production (see validate_production_secrets). Dev may raise it for
    # convenience.
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1)
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

    # Custom symptom slug HMAC (ADR-0039, Issue #62) — separate from ENCRYPTION_KEY.
    # Generate: python -c "import secrets; print(secrets.token_hex(32))"
    SLUG_HMAC_KEY: str = "CHANGE_ME_slug_hmac_key_min_32_bytes"

    # MinIO / S3 (photo storage — ships in M13). Gated by PHOTOS_ENABLED so the
    # secret is only required once photos are actually turned on (#543).
    PHOTOS_ENABLED: bool = False
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

    # Capacitor Android WebView origin (`androidScheme: 'https'` → https://localhost).
    # Always merged into the effective allowlist so sideload/selfhost APKs can
    # call the API without every .env remembering this origin (M11).
    CAPACITOR_CORS_ORIGINS: tuple[str, ...] = ("https://localhost",)

    @property
    def cors_allow_origins(self) -> list[str]:
        """CORS_ORIGINS plus required Capacitor WebView origins (deduped)."""
        seen: list[str] = []
        for origin in [*self.CORS_ORIGINS, *self.CAPACITOR_CORS_ORIGINS]:
            cleaned = origin.strip()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        return seen

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

    # Worker robustness (#753): hard ceilings so a stuck query, a held
    # advisory lock, or a runaway per-user job cannot hang a connection or
    # the nightly batch indefinitely. Milliseconds, mirrors Postgres units.
    DB_STATEMENT_TIMEOUT_MS: int = Field(default=30_000, ge=1_000)
    DB_LOCK_TIMEOUT_MS: int = Field(default=5_000, ge=1_000)
    # Per-user insight/digest job wall-clock ceiling inside the worker loop.
    WORKER_JOB_TIMEOUT_SECONDS: int = Field(default=180, ge=10)
    # Retry/backoff for the insight-generation advisory lock (#753 Option H).
    INSIGHT_LOCK_MAX_ATTEMPTS: int = Field(default=3, ge=1)
    INSIGHT_LOCK_RETRY_BACKOFF_SECONDS: float = Field(default=0.5, ge=0.0)

    # Fault-tolerance refinement (#758). K — transient vs. permanent error
    # classification: a connection reset or lock timeout gets a short in-run
    # retry before the user is marked failed, while a permanent data error is
    # not retried. Number of extra attempts after the first (0 disables retry).
    WORKER_TRANSIENT_MAX_RETRIES: int = Field(default=2, ge=0)
    WORKER_TRANSIENT_RETRY_BACKOFF_SECONDS: float = Field(default=0.5, ge=0.0)
    # L — poison-pill escalation: once a single user's insight generation has
    # failed this many scheduled runs in a row (e.g. a corrupt DEK), the worker
    # logs a loud escalation instead of one quiet line per night. Capped at 20
    # to mirror worker_run_service.PER_USER_RETENTION: only the newest 20
    # per-user runs are retained, so a streak can never exceed that and a
    # higher threshold could never fire (#772 review).
    WORKER_POISON_PILL_THRESHOLD: int = Field(default=3, ge=1, le=20)

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

    # Optional Ollama-backed insight statements (#148).
    INSIGHTS_LLM_ENABLED: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    # Changepoint detection minimum mood samples (#149).
    ANALYTICS_MIN_ENTRIES_CHANGEPOINT: int = Field(default=60, ge=2)

    # Error tracking (M9) — optional selfhosted GlitchTip via Sentry protocol.
    # Leave empty for zero outbound error-reporting traffic.
    GLITCHTIP_DSN: str = ""
    GLITCHTIP_ENVIRONMENT: str = ""
    GLITCHTIP_TRACES_SAMPLE_RATE: float = Field(default=0.0, ge=0.0, le=1.0)

    # FCM (M11 Sprint 5) — SaaS / Play builds only. Selfhost leaves this off;
    # UnifiedPush remains the M4.2 primary for privacy installs.
    FCM_ENABLED: bool = False
    # Inline service-account JSON (preferred in container secrets) OR path via
    # GOOGLE_APPLICATION_CREDENTIALS. Requires optional extra: correlcore-backend[fcm].
    FCM_CREDENTIALS_JSON: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

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
        """Effective Secure-Flag for auth cookies without a request (ADR-0006).

        - Wenn ``COOKIE_SECURE`` explizit ``True``/``False`` gesetzt ist, gilt
          das (mit Production-Sicherheits-Override im Validator).
        - Wenn ``None`` (Default), schalten wir ``Secure`` nur in
          ``APP_ENV=development`` aus; alle anderen Umgebungen (staging,
          production) starten mit ``Secure=True``.

        Beim Setzen von Cookies bevorzugt ``cookie_secure_for_request``
        (``app.core.auth_cookies``) zusätzlich ``X-Forwarded-Proto`` in
        Non-Production, damit HTTP-Tailscale-Proxies ohne manuelles
        ``COOKIE_SECURE=false`` funktionieren. Homelab-Compose-Defaults
        setzen trotzdem ``COOKIE_SECURE=false``.
        """
        if self.COOKIE_SECURE is not None:
            return self.COOKIE_SECURE
        return self.APP_ENV.lower() != "development"

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        env = self.APP_ENV.lower()
        if env in {"production", "staging"}:
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
            # Fail closed on invalid Fernet material (not only CHANGE_ME prefix).
            try:
                from cryptography.fernet import Fernet, MultiFernet

                MultiFernet([Fernet(k.encode("utf-8")) for k in keys])
            except Exception as exc:
                raise ValueError(
                    "ENCRYPTION_KEY (or ENCRYPTION_KEYS) must be a valid Fernet key. "
                    "Generate with: python -c 'from cryptography.fernet import Fernet; "
                    "print(Fernet.generate_key().decode())'"
                ) from exc
            if self.SLUG_HMAC_KEY.startswith("CHANGE_ME") or len(self.SLUG_HMAC_KEY) < 32:
                raise ValueError(
                    "SLUG_HMAC_KEY must be set to at least 32 random characters in "
                    "production. Generate with: "
                    "python -c 'import secrets; print(secrets.token_hex(32))'"
                )
            if not self.CORS_ORIGINS or any(o.strip() == "*" for o in self.CORS_ORIGINS):
                raise ValueError(
                    "CORS_ORIGINS must be an explicit non-empty allowlist "
                    "(wildcard '*' is not allowed) in staging/production"
                )
            # ADR-0006 L1: the "no logout denylist" residual is only acceptable
            # while access tokens are short-lived (#791). Refuse a TTL that would
            # leave a stolen token usable well past logout.
            if self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > PROD_MAX_ACCESS_TOKEN_EXPIRE_MINUTES:
                raise ValueError(
                    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be "
                    f"≤ {PROD_MAX_ACCESS_TOKEN_EXPIRE_MINUTES} in staging/production "
                    "(ADR-0006 L1: there is no logout denylist, so a long-lived "
                    "access token stays usable after logout). Lower the TTL or "
                    "amend ADR-0006 before raising this bound."
                )
        # Production hard-blocks debug/ops surfaces. The MinIO secret is only
        # required once photo storage is enabled (PHOTOS_ENABLED, M13) — until
        # then the placeholder is fine even in production (#543).
        if env == "production":
            if self.DEBUG:
                raise ValueError("DEBUG=true is not allowed when APP_ENV=production")
            if self.DEV_VIEW_ENABLED:
                raise ValueError("DEV_VIEW_ENABLED=true is not allowed when APP_ENV=production")
            if self.PHOTOS_ENABLED and (
                self.MINIO_SECRET_KEY.startswith("CHANGE_ME") or len(self.MINIO_SECRET_KEY) < 16
            ):
                raise ValueError(
                    "MINIO_SECRET_KEY must be set to a non-default secret "
                    "(≥16 characters) when PHOTOS_ENABLED=true in production"
                )
        # ADR-0006: Secure ist in Produktion nicht abschaltbar. Staging darf
        # COOKIE_SECURE=false setzen (Homelab-HTTP-Setups), Production nicht.
        if env == "production" and self.COOKIE_SECURE is False:
            raise ValueError(
                "COOKIE_SECURE=false ist in APP_ENV=production nicht erlaubt "
                "(ADR-0006: Secure-Flag verbindlich). Bitte HTTPS terminieren "
                "(z. B. Reverse-Proxy mit TLS) und COOKIE_SECURE entfernen "
                "oder auf true setzen."
            )
        return self


settings = Settings()
