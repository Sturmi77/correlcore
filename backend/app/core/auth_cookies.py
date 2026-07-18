"""Shared auth-cookie helpers.

The auth and user routers both need to set or clear the same HttpOnly
cookies. Keeping names, paths, and security attributes in one module avoids
silent drift: a path change in the login flow must also affect logout,
refresh-error cleanup, and DSGVO account deletion.

``remember_me`` (Issue #453 / ADR-0006 persistent session):
- ``True`` (default): persistent cookies with ``Max-Age`` (refresh TTL).
- ``False``: session cookies (no ``Max-Age``) — cleared when the browser
  session ends. Used for Web/PWA „Angemeldet bleiben“ off.
"""

from __future__ import annotations

from fastapi import Response

from app.core.config import settings

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
ACCESS_COOKIE_PATH = "/api"
REFRESH_COOKIE_PATH = "/api/v1/auth/refresh"
ACCESS_COOKIE_MAX_AGE_SECONDS = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_COOKIE_MAX_AGE_SECONDS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86_400


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    *,
    remember_me: bool = True,
) -> None:
    """Attach access and refresh cookies with ADR-0004/-0006 security attributes.

    ``Secure`` wird über ``settings.cookie_secure_effective`` gesteuert
    (Default: True ausser ``APP_ENV=development`` oder explizit
    ``COOKIE_SECURE=false``). Hartkodiertes ``secure=True`` würde Browser
    bei HTTP-Origins (lokales Tailscale-/Homelab-Setup ohne TLS) dazu
    bringen, das Set-Cookie zu verwerfen — Login-Flow scheitert dann
    stillschweigend. ADR-0006 stellt sicher, dass Production weiterhin
    zwangsweise Secure verwendet.

    When ``remember_me`` is false, omit ``max_age`` so cookies are
    browser-session scoped (Web/PWA).
    """
    secure = settings.cookie_secure_effective
    if remember_me:
        response.set_cookie(
            key=ACCESS_COOKIE_NAME,
            value=access_token,
            httponly=True,
            secure=secure,
            samesite="strict",
            path=ACCESS_COOKIE_PATH,
            max_age=ACCESS_COOKIE_MAX_AGE_SECONDS,
        )
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            secure=secure,
            samesite="strict",
            path=REFRESH_COOKIE_PATH,
            max_age=REFRESH_COOKIE_MAX_AGE_SECONDS,
        )
    else:
        response.set_cookie(
            key=ACCESS_COOKIE_NAME,
            value=access_token,
            httponly=True,
            secure=secure,
            samesite="strict",
            path=ACCESS_COOKIE_PATH,
        )
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            secure=secure,
            samesite="strict",
            path=REFRESH_COOKIE_PATH,
        )


def clear_auth_cookies(response: Response) -> None:
    """Clear both auth cookies using the same path/secure/samesite as set.

    Chromium only clears a ``Secure`` cookie when the clearing ``Set-Cookie``
    also carries ``Secure`` (and matching path). Starlette's defaults would
    leave sessions in the jar after logout on HTTPS deployments.
    """
    secure = settings.cookie_secure_effective
    response.delete_cookie(
        ACCESS_COOKIE_NAME,
        path=ACCESS_COOKIE_PATH,
        secure=secure,
        httponly=True,
        samesite="strict",
    )
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=secure,
        httponly=True,
        samesite="strict",
    )
