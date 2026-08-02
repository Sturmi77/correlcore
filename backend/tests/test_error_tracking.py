"""Tests for optional GlitchTip / Sentry error tracking (M9 Sprint 2)."""

from __future__ import annotations

from unittest.mock import patch

from app.core.config import Settings
from app.core.error_tracking import init_error_tracking, scrub_mapping, scrub_sentry_event


def test_scrub_mapping_redacts_health_fields_and_email() -> None:
    scrubbed = scrub_mapping(
        {
            "mood_score": 4,
            "cycle_day": 12,
            "cycle_bleeding_level": "medium",
            "sleep_minutes": 420,
            "sleep_quality": 4,
            "note": "Heute Migräne",
            "email": "alice@example.com",
            "user_id": "00000000-0000-4000-8000-000000000001",
        }
    )

    assert scrubbed["mood_score"] == "[Filtered]"
    assert scrubbed["cycle_day"] == "[Filtered]"
    assert scrubbed["cycle_bleeding_level"] == "[Filtered]"
    assert scrubbed["sleep_minutes"] == "[Filtered]"
    assert scrubbed["sleep_quality"] == "[Filtered]"
    assert scrubbed["note"] == "[Filtered]"
    assert scrubbed["email"] == "[Filtered]"
    assert scrubbed["user_id"] == "00000000-0000-4000-8000-000000000001"


def test_scrub_sentry_event_strips_request_payload_and_cookies() -> None:
    event = {
        "message": "validation failed for alice@example.com",
        "request": {
            "data": {
                "password": "CorrectHorse123!",
                "mood_score": 2,
                "cycle_day": 8,
                "cycle_bleeding_level": "heavy",
                "sleep_minutes": 390,
                "sleep_quality": 3,
                "note": "private journal",
            },
            "cookies": {"access_token": "secret", "refresh_token": "secret2"},
            "headers": {"authorization": "Bearer token", "x-request-id": "req-1"},
        },
        "user": {"email": "alice@example.com", "id": "user-1"},
        "extra": {"symptoms": [{"slug": "headache"}]},
    }

    scrubbed = scrub_sentry_event(event, {})

    assert scrubbed is not None
    assert scrubbed["request"]["data"]["password"] == "[Filtered]"
    assert scrubbed["request"]["data"]["mood_score"] == "[Filtered]"
    assert scrubbed["request"]["data"]["cycle_day"] == "[Filtered]"
    assert scrubbed["request"]["data"]["cycle_bleeding_level"] == "[Filtered]"
    assert scrubbed["request"]["data"]["sleep_minutes"] == "[Filtered]"
    assert scrubbed["request"]["data"]["sleep_quality"] == "[Filtered]"
    assert scrubbed["request"]["data"]["note"] == "[Filtered]"
    assert scrubbed["request"]["cookies"]["access_token"] == "[Filtered]"
    assert scrubbed["request"]["headers"]["authorization"] == "[Filtered]"
    assert scrubbed["request"]["headers"]["x-request-id"] == "req-1"
    assert scrubbed["user"]["email"] == "[Filtered]"
    assert scrubbed["user"]["id"] == "user-1"
    assert scrubbed["extra"]["symptoms"] == "[Filtered]"
    assert "alice@example.com" not in scrubbed["message"]


def test_init_error_tracking_skips_without_dsn() -> None:
    settings = Settings(GLITCHTIP_DSN="")

    with patch("sentry_sdk.init") as init_mock:
        enabled = init_error_tracking(settings)

    assert enabled is False
    init_mock.assert_not_called()


def test_init_error_tracking_initialises_when_dsn_set() -> None:
    settings = Settings(
        GLITCHTIP_DSN="https://example.com/1",
        APP_ENV="staging",
        APP_VERSION="0.0.1",
    )

    with patch("sentry_sdk.init") as init_mock:
        enabled = init_error_tracking(settings)

    assert enabled is True
    init_mock.assert_called_once()
    kwargs = init_mock.call_args.kwargs
    assert kwargs["dsn"] == "https://example.com/1"
    assert kwargs["environment"] == "staging"
    assert kwargs["send_default_pii"] is False
    assert kwargs["traces_sample_rate"] == 0.0
    assert kwargs["before_send"].__name__ == "_before_send"
