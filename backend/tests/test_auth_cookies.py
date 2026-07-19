"""Unit tests for ``app.core.auth_cookies``.

Targets the ADR-0006 fix that wires ``Secure`` to
``cookie_secure_for_request`` / ``settings.cookie_secure_effective``
instead of a hardcoded ``True``.
We assert at the FastAPI ``Response`` boundary so we cover the actual
``Set-Cookie`` header bytes the browser will see.
"""

from __future__ import annotations

import logging

import pytest
from fastapi import Response
from starlette.requests import Request

from app.core import auth_cookies


def _set_cookie_lines(response: Response) -> list[str]:
    """Collect every Set-Cookie raw header line on the response."""
    return [
        value.decode("latin-1")
        for key, value in response.raw_headers
        if key.decode("latin-1").lower() == "set-cookie"
    ]


def _request_with_proto(proto: str | None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if proto is not None:
        headers.append((b"x-forwarded-proto", proto.encode("latin-1")))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/auth/login",
        "raw_path": b"/api/v1/auth/login",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
    }
    return Request(scope)


@pytest.fixture
def fresh_response() -> Response:
    return Response()


def test_set_auth_cookies_omits_secure_in_dev(
    fresh_response: Response, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With ``cookie_secure_effective=False`` no Secure attribute is emitted."""
    monkeypatch.setattr(auth_cookies.settings, "COOKIE_SECURE", False, raising=False)
    auth_cookies.set_auth_cookies(fresh_response, "access-jwt", "refresh-jwt")

    lines = _set_cookie_lines(fresh_response)
    assert len(lines) == 2
    joined = "\n".join(lines)
    assert "access_token=access-jwt" in joined
    assert "refresh_token=refresh-jwt" in joined
    # No Secure flag means the browser will accept the cookie on plain HTTP.
    assert "Secure" not in joined
    # Other attributes from ADR-0004/-0006 must remain intact.
    assert "HttpOnly" in joined
    assert "SameSite=strict" in joined
    assert "Path=/api;" in joined or "Path=/api," in joined or "; Path=/api" in joined
    assert "/api/v1/auth/refresh" in joined


def test_set_auth_cookies_emits_secure_when_enabled(
    fresh_response: Response, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With ``cookie_secure_effective=True`` both cookies must carry Secure."""
    monkeypatch.setattr(auth_cookies.settings, "COOKIE_SECURE", True, raising=False)
    auth_cookies.set_auth_cookies(fresh_response, "access-jwt", "refresh-jwt")

    lines = _set_cookie_lines(fresh_response)
    assert len(lines) == 2
    for line in lines:
        assert "Secure" in line
        assert "HttpOnly" in line
        assert "SameSite=strict" in line


def test_set_auth_cookies_remember_me_true_sets_max_age(
    fresh_response: Response, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Persistent session (default) must emit Max-Age on both cookies."""
    monkeypatch.setattr(auth_cookies.settings, "COOKIE_SECURE", False, raising=False)
    auth_cookies.set_auth_cookies(fresh_response, "access-jwt", "refresh-jwt", remember_me=True)

    lines = _set_cookie_lines(fresh_response)
    assert len(lines) == 2
    for line in lines:
        assert "Max-Age=" in line


def test_set_auth_cookies_remember_me_false_omits_max_age(
    fresh_response: Response, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Session cookies for remember_me=false must not carry Max-Age."""
    monkeypatch.setattr(auth_cookies.settings, "COOKIE_SECURE", False, raising=False)
    auth_cookies.set_auth_cookies(fresh_response, "access-jwt", "refresh-jwt", remember_me=False)

    lines = _set_cookie_lines(fresh_response)
    assert len(lines) == 2
    for line in lines:
        assert "Max-Age=" not in line


def test_clear_auth_cookies_uses_matching_paths(
    fresh_response: Response, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Logout/account-delete must clear both cookies on the original paths.

    A path mismatch would leave the cookie in the jar — RFC 6265 requires
    the delete-cookie to match path + name. Secure/SameSite/HttpOnly must
    also match the set attributes so HTTPS browsers actually drop them.
    """
    monkeypatch.setattr(auth_cookies.settings, "COOKIE_SECURE", True, raising=False)
    auth_cookies.clear_auth_cookies(fresh_response)

    lines = _set_cookie_lines(fresh_response)
    assert len(lines) == 2
    joined = "\n".join(lines)
    assert "access_token=" in joined
    assert "refresh_token=" in joined
    assert "/api/v1/auth/refresh" in joined
    assert "Path=/api" in joined
    for line in lines:
        assert "Secure" in line
        assert "HttpOnly" in line
        assert "SameSite=strict" in line


# ---------------------------------------------------------------------------
# Request-aware Secure (X-Forwarded-Proto) — Homelab HTTP Tailscale path
# ---------------------------------------------------------------------------


def test_cookie_secure_for_request_honors_explicit_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_cookies.settings, "COOKIE_SECURE", False, raising=False)
    monkeypatch.setattr(auth_cookies.settings, "APP_ENV", "staging", raising=False)
    assert auth_cookies.cookie_secure_for_request(_request_with_proto("https")) is False


def test_cookie_secure_for_request_production_always_secure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even with X-Forwarded-Proto=http, production must stay Secure."""
    monkeypatch.setattr(auth_cookies.settings, "COOKIE_SECURE", None, raising=False)
    monkeypatch.setattr(auth_cookies.settings, "APP_ENV", "production", raising=False)
    assert auth_cookies.cookie_secure_for_request(_request_with_proto("http")) is True


def test_cookie_secure_for_request_staging_http_proto_disables_secure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """user-test / dockge: APP_ENV=staging + proxy proto http → no Secure.

    This is the live failure mode: login 200 + Set-Cookie Secure on
    http://100.x:3000 → browser discards cookies → 401 Could not validate
    credentials on the next /api call.
    """
    monkeypatch.setattr(auth_cookies.settings, "COOKIE_SECURE", None, raising=False)
    monkeypatch.setattr(auth_cookies.settings, "APP_ENV", "staging", raising=False)
    assert auth_cookies.cookie_secure_for_request(_request_with_proto("http")) is False


def test_cookie_secure_for_request_staging_https_proto_enables_secure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_cookies.settings, "COOKIE_SECURE", None, raising=False)
    monkeypatch.setattr(auth_cookies.settings, "APP_ENV", "staging", raising=False)
    assert auth_cookies.cookie_secure_for_request(_request_with_proto("https")) is True


def test_cookie_secure_for_request_staging_without_proto_defaults_secure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_cookies.settings, "COOKIE_SECURE", None, raising=False)
    monkeypatch.setattr(auth_cookies.settings, "APP_ENV", "staging", raising=False)
    assert auth_cookies.cookie_secure_for_request(_request_with_proto(None)) is True
    assert auth_cookies.cookie_secure_for_request(None) is True


def test_set_auth_cookies_omits_secure_when_forwarded_proto_http(
    fresh_response: Response, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(auth_cookies.settings, "COOKIE_SECURE", None, raising=False)
    monkeypatch.setattr(auth_cookies.settings, "APP_ENV", "staging", raising=False)
    req = _request_with_proto("http")
    auth_cookies.set_auth_cookies(fresh_response, "access-jwt", "refresh-jwt", request=req)
    joined = "\n".join(_set_cookie_lines(fresh_response))
    assert "Secure" not in joined
    assert "access_token=access-jwt" in joined


def test_warn_if_http_staging_may_drop_cookies_logs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(auth_cookies.settings, "COOKIE_SECURE", None, raising=False)
    monkeypatch.setattr(auth_cookies.settings, "APP_ENV", "staging", raising=False)
    with caplog.at_level(logging.WARNING, logger="app.core.auth_cookies"):
        auth_cookies.warn_if_http_staging_may_drop_cookies()
    assert any("COOKIE_SECURE unset" in r.message for r in caplog.records)
