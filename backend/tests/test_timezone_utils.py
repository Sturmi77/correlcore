"""Timezone resolution + log-safety for the client-supplied `tz` parameter (#892)."""

from __future__ import annotations

import errno
import logging
import time

import pytest

from app.services import timezone_utils
from app.services.timezone_utils import UTC_ZONE, _log_safe_tz, resolve_zone


def test_resolve_zone_accepts_iana_names() -> None:
    assert resolve_zone("Europe/Vienna").key == "Europe/Vienna"


@pytest.mark.parametrize("value", [None, "", "Not/AZone", "🙂"])
def test_resolve_zone_degrades_to_utc(value: str | None) -> None:
    """A device TZ quirk must never break entry create or widget summaries."""
    assert resolve_zone(value) is UTC_ZONE


def test_unknown_but_well_shaped_name_is_logged_verbatim(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        resolve_zone("Mars/Olympus_Mons")
    assert caplog.records[-1].timezone == "Mars/Olympus_Mons"  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "hostile",
    [
        "Europe/Vienna\nINFO fake.log.entry: pwned",
        "Europe/Vienna\r\nWARNING injected",
        "Europe/Vienna line-separator",
        "A" * 200,
        # py/polynomial-redos: the earlier fullmatch guard backtracked on these
        # because its segment class contained '+'. The whitelist test cannot.
        "+" * 60,
        "Europe/" + "+" * 50 + "!",
        "a/b/c/d/e/f",
    ],
)
def test_log_injection_payloads_never_reach_the_log(
    hostile: str, caplog: pytest.LogCaptureFixture
) -> None:
    """CodeQL py/log-injection: `tz` is a query parameter and stays out of the log.

    A whole-string match against the IANA shape is the barrier — substituting the
    unsafe characters away is not modelled as a sanitizer, so the alert survived
    that earlier rewrite.
    """
    assert _log_safe_tz(hostile) == "<invalid>"
    with caplog.at_level(logging.INFO):
        assert resolve_zone(hostile) is UTC_ZONE
    logged = caplog.records[-1].timezone  # type: ignore[attr-defined]
    assert logged == "<invalid>"
    assert "\n" not in logged and "\r" not in logged


def test_log_safe_tz_is_linear_on_adversarial_repetition() -> None:
    """No regex, so a pathological string cannot burn CPU in the log path."""
    payload = "+" * 5_000 + "!"
    started = time.perf_counter()
    assert _log_safe_tz(payload) == "<invalid>"
    assert time.perf_counter() - started < 0.1


def test_well_shaped_three_segment_name_survives() -> None:
    assert _log_safe_tz("America/Argentina/Buenos_Aires") == "America/Argentina/Buenos_Aires"


@pytest.mark.parametrize(
    ("errno_value", "winerror"),
    [
        (errno.EINVAL, None),
        (None, 123),  # ERROR_INVALID_NAME
        (None, 206),  # ERROR_FILENAME_EXCED_RANGE
    ],
)
def test_expected_zone_path_os_errors_degrade_to_utc(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    errno_value: int | None,
    winerror: int | None,
) -> None:
    class WindowsZoneError(OSError):
        pass

    error = WindowsZoneError(errno_value or 0, "invalid timezone path")
    if winerror is not None:
        error.winerror = winerror  # type: ignore[attr-defined]

    def raise_zone_error(_value: str) -> None:
        raise error

    monkeypatch.setattr(timezone_utils, "ZoneInfo", raise_zone_error)
    with caplog.at_level(logging.INFO):
        assert resolve_zone("Mars/Olympus_Mons") is UTC_ZONE
    assert caplog.records[-1].timezone == "Mars/Olympus_Mons"  # type: ignore[attr-defined]


def test_unexpected_zone_filesystem_errors_are_not_suppressed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_permission_error(_value: str) -> None:
        raise PermissionError(13, "tzdata access denied")

    monkeypatch.setattr(timezone_utils, "ZoneInfo", raise_permission_error)
    with pytest.raises(PermissionError, match="tzdata access denied"):
        resolve_zone("Europe/Vienna")


@pytest.mark.parametrize(
    "invalid",
    [
        "Europe/Vienna\nInjected",
        "Europe/Vienna\r\nInjected",
        "../Europe/Vienna",
        "A" * 65,
    ],
)
def test_invalid_shape_never_reaches_platform_zone_lookup(
    monkeypatch: pytest.MonkeyPatch,
    invalid: str,
) -> None:
    called = False

    def record_call(_value: str) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(timezone_utils, "ZoneInfo", record_call)
    assert resolve_zone(invalid) is UTC_ZONE
    assert called is False
