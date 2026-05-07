"""Regression tests for CSV-encoded list fields in Settings.

Background
----------
``CORS_ORIGINS`` and ``ENCRYPTION_KEYS`` are typed ``list[str]``. Without
explicit opt-out, ``pydantic-settings`` tries to JSON-decode environment
values for complex fields *before* any ``field_validator`` runs, which
raised ``SettingsError: error parsing value for field "CORS_ORIGINS"`` at
container start when operators set the variables as comma-separated
strings (the documented format in ``infra/docker/.env.example``).

The fix annotates both fields with ``NoDecode`` so the existing
``mode="before"`` validators see the raw string and split on commas.
These tests guard that contract.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings


@pytest.fixture(autouse=True)
def _stable_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide non-CHANGE_ME defaults so the production-secret model_validator
    does not interfere with these focused tests."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv(
        "ENCRYPTION_KEY",
        "0123456789abcdef0123456789abcdef0123456789abcdef01234=",
    )
    # Clear any .env discovery from the repo root during pytest runs.
    monkeypatch.chdir("/")


def _make_settings() -> Settings:
    # ``_env_file=None`` ensures we read only the monkeypatched env, never a
    # stray ``.env`` file in the working tree.
    return Settings(_env_file=None)  # type: ignore[call-arg]


class TestCorsOrigins:
    def test_csv_string_is_split_into_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "CORS_ORIGINS",
            "http://100.120.157.82:3000,http://localhost:3000",
        )
        settings = _make_settings()
        assert settings.CORS_ORIGINS == [
            "http://100.120.157.82:3000",
            "http://localhost:3000",
        ]

    def test_csv_string_with_whitespace_is_trimmed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CORS_ORIGINS", "  http://a.example , http://b.example  ")
        settings = _make_settings()
        assert settings.CORS_ORIGINS == ["http://a.example", "http://b.example"]

    def test_single_origin_without_comma(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
        settings = _make_settings()
        assert settings.CORS_ORIGINS == ["http://localhost:3000"]

    def test_default_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        settings = _make_settings()
        assert settings.CORS_ORIGINS == [
            "http://localhost:5173",
            "http://localhost:3000",
        ]


class TestEncryptionKeys:
    def test_csv_string_is_split_into_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENCRYPTION_KEYS", "key-one,key-two,key-three")
        settings = _make_settings()
        assert settings.ENCRYPTION_KEYS == ["key-one", "key-two", "key-three"]

    def test_empty_string_yields_empty_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENCRYPTION_KEYS", "")
        settings = _make_settings()
        assert settings.ENCRYPTION_KEYS == []

    def test_unset_yields_empty_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ENCRYPTION_KEYS", raising=False)
        settings = _make_settings()
        assert settings.ENCRYPTION_KEYS == []

    def test_effective_keys_falls_back_to_scalar(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ENCRYPTION_KEYS", raising=False)
        monkeypatch.setenv("ENCRYPTION_KEY", "fallback-master-key")
        settings = _make_settings()
        assert settings.effective_encryption_keys() == ["fallback-master-key"]

    def test_effective_keys_prefers_list_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENCRYPTION_KEYS", "primary,secondary")
        monkeypatch.setenv("ENCRYPTION_KEY", "ignored-fallback")
        settings = _make_settings()
        assert settings.effective_encryption_keys() == ["primary", "secondary"]
