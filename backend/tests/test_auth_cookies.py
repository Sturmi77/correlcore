"""Unit tests for ``app.core.auth_cookies``.

Targets the ADR-0006 fix that wires ``Secure`` to
``settings.cookie_secure_effective`` instead of a hardcoded ``True``.
We assert at the FastAPI ``Response`` boundary so we cover the actual
``Set-Cookie`` header bytes the browser will see.
"""

from __future__ import annotations

import pytest
from fastapi import Response

from app.core import auth_cookies


def _set_cookie_lines(response: Response) -> list[str]:
    """Collect every Set-Cookie raw header line on the response."""
    return [
        value.decode("latin-1")
        for key, value in response.raw_headers
        if key.decode("latin-1").lower() == "set-cookie"
    ]


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
