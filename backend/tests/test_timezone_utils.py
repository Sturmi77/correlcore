"""Timezone resolution + log-safety for the client-supplied `tz` parameter (#892)."""

from __future__ import annotations

import logging

import pytest

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
