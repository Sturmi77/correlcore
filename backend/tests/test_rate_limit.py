"""Rate-limit key selection tests."""

from __future__ import annotations

from unittest.mock import patch

from starlette.requests import Request

from app.core.rate_limit import rate_limit_key


def _request(
    headers: dict[str, str] | None = None,
    client: tuple[str, int] | None = None,
) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in (headers or {}).items()
        ],
        "client": client or ("10.0.0.10", 12345),
    }
    return Request(scope)


def test_rate_limit_key_defaults_to_tcp_peer_even_when_xff_is_present() -> None:
    with patch("app.core.rate_limit.settings") as settings:
        settings.RATE_LIMIT_TRUST_PROXY_HEADERS = False
        assert rate_limit_key(_request({"x-forwarded-for": "203.0.113.8"})) == "10.0.0.10"


def test_rate_limit_key_uses_last_forwarded_for_when_proxy_headers_are_trusted() -> None:
    with patch("app.core.rate_limit.settings") as settings:
        settings.RATE_LIMIT_TRUST_PROXY_HEADERS = True
        request = _request({"x-forwarded-for": "198.51.100.1, 203.0.113.8"})
        assert rate_limit_key(request) == "203.0.113.8"


def test_rate_limit_key_falls_back_to_x_real_ip_when_trusted_and_no_xff() -> None:
    with patch("app.core.rate_limit.settings") as settings:
        settings.RATE_LIMIT_TRUST_PROXY_HEADERS = True
        assert rate_limit_key(_request({"x-real-ip": "203.0.113.9"})) == "203.0.113.9"
