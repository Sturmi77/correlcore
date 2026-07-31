"""Production/staging Settings guards added in the 2026-07-16 audit."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

_VALID_FERNET = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


@pytest.fixture(autouse=True)
def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "APP_ENV",
        "COOKIE_SECURE",
        "DEBUG",
        "DEV_VIEW_ENABLED",
        "MINIO_SECRET_KEY",
        "PHOTOS_ENABLED",
        "CORS_ORIGINS",
        "SECRET_KEY",
        "ENCRYPTION_KEY",
        "SLUG_HMAC_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://t:t@localhost/t")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("ENCRYPTION_KEY", _VALID_FERNET)
    monkeypatch.setenv("SLUG_HMAC_KEY", "test-slug-hmac-key-for-production-guards-32")
    monkeypatch.setenv("MINIO_SECRET_KEY", "test-minio-secret-not-default")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")


def test_production_rejects_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "true")
    with pytest.raises(ValidationError, match="DEBUG"):
        Settings()


def test_production_rejects_dev_view(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEV_VIEW_ENABLED", "true")
    with pytest.raises(ValidationError, match="DEV_VIEW_ENABLED"):
        Settings()


def test_production_allows_default_minio_when_photos_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Photo storage ships in M13; until PHOTOS_ENABLED the placeholder is fine (#543)."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MINIO_SECRET_KEY", "CHANGE_ME_MINIO_SECRET")
    s = Settings()
    assert s.PHOTOS_ENABLED is False


def test_production_rejects_default_minio_when_photos_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PHOTOS_ENABLED", "true")
    monkeypatch.setenv("MINIO_SECRET_KEY", "CHANGE_ME_MINIO_SECRET")
    with pytest.raises(ValidationError, match="MINIO_SECRET_KEY"):
        Settings()


def test_production_rejects_wildcard_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings()


def test_production_rejects_invalid_fernet(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENCRYPTION_KEY", "not-a-valid-fernet-key-but-long-enough-xx")
    with pytest.raises(ValidationError, match="Fernet"):
        Settings()


def test_staging_allows_dev_view_and_default_minio(monkeypatch: pytest.MonkeyPatch) -> None:
    """Homelab staging may enable /dev; MinIO placeholder OK until M13."""
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("DEV_VIEW_ENABLED", "true")
    monkeypatch.setenv("MINIO_SECRET_KEY", "CHANGE_ME_MINIO_SECRET")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    s = Settings()
    assert s.DEV_VIEW_ENABLED is True


def test_production_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    s = Settings()
    assert s.cookie_secure_effective is True
    assert s.DEBUG is False
    assert s.DEV_VIEW_ENABLED is False


@pytest.mark.parametrize("app_env", ["production ", " production", "production\t", "PRODUCTION "])
def test_production_guards_apply_when_app_env_has_whitespace(
    monkeypatch: pytest.MonkeyPatch, app_env: str
) -> None:
    """Whitespace around APP_ENV must not skip staging/production secret guards."""
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_MIN_32_BYTES_RANDOM")
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings()


def test_production_whitespace_rejects_debug_and_insecure_cookies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production ")
    monkeypatch.setenv("DEBUG", "true")
    with pytest.raises(ValidationError, match="DEBUG"):
        Settings()

    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings()


def test_production_whitespace_normalizes_app_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "  production  ")
    s = Settings()
    assert s.APP_ENV == "production"
    assert s.cookie_secure_effective is True
