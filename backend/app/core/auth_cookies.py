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

import logging

from fastapi import Response
from starlette.requests import Request

from app.core.config import settings

logger = logging.getLogger(__name__)

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
ACCESS_COOKIE_PATH = "/api"
REFRESH_COOKIE_PATH = "/api/v1/auth/refresh"
ACCESS_COOKIE_MAX_AGE_SECONDS = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_COOKIE_MAX_AGE_SECONDS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86_400


def _forwarded_proto(request: Request) -> str | None:
    """First ``X-Forwarded-Proto`` value, lowercased (``http`` / ``https``)."""
    raw = request.headers.get("x-forwarded-proto", "")
    if not raw:
        return None
    proto = raw.split(",")[0].strip().lower()
    if proto in {"http", "https"}:
        return proto
    return None


def cookie_secure_for_request(request: Request | None = None) -> bool:
    """Resolve the ``Secure`` flag for auth cookies on this response (ADR-0006).

    Precedence:
    1. Explicit ``COOKIE_SECURE`` env (production forbids ``false``).
    2. ``APP_ENV=production`` → always ``True``.
    3. ``APP_ENV=development`` → ``False`` (local Vite HTTP).
    4. Staging / other + request with ``X-Forwarded-Proto`` → match scheme
       (SvelteKit ``hooks.server.ts`` overwrites this header from the browser
       URL, so plain-HTTP Tailscale origins get non-Secure cookies without
       requiring operators to remember ``COOKIE_SECURE=false``).
    5. Else → ``True`` (HTTPS staging assumption).
    """
    if settings.COOKIE_SECURE is not None:
        return settings.COOKIE_SECURE

    env = settings.APP_ENV.lower()
    if env == "production":
        return True
    if env == "development":
        return False

    if request is not None:
        proto = _forwarded_proto(request)
        if proto == "http":
            return False
        if proto == "https":
            return True

    return True


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    *,
    remember_me: bool = True,
    request: Request | None = None,
) -> None:
    """Attach access and refresh cookies with ADR-0004/-0006 security attributes.

    ``Secure`` wird über :func:`cookie_secure_for_request` gesteuert
    (explizites ``COOKIE_SECURE``, sonst APP_ENV + optional
    ``X-Forwarded-Proto``). Hartkodiertes ``secure=True`` würde Browser
    bei HTTP-Origins (lokales Tailscale-/Homelab-Setup ohne TLS) dazu
    bringen, das Set-Cookie zu verwerfen — Login-Flow scheitert dann
    stillschweigend mit Folge-401 ``Could not validate credentials``.
    ADR-0006 stellt sicher, dass Production weiterhin zwangsweise Secure
    verwendet.

    When ``remember_me`` is false, omit ``max_age`` so cookies are
    browser-session scoped (Web/PWA).
    """
    secure = cookie_secure_for_request(request)
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


def clear_auth_cookies(response: Response, *, request: Request | None = None) -> None:
    """Clear both auth cookies using the same path/secure/samesite as set.

    Chromium only clears a ``Secure`` cookie when the clearing ``Set-Cookie``
    also carries ``Secure`` (and matching path). Starlette's defaults would
    leave sessions in the jar after logout on HTTPS deployments.
    """
    secure = cookie_secure_for_request(request)
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


def warn_if_http_staging_may_drop_cookies() -> None:
    """Log an ops hint when staging defaults would emit Secure cookies.

    Homelab stacks that forget ``COOKIE_SECURE=false`` used to fail silently
    after login. Request-aware ``X-Forwarded-Proto`` mitigates the common
    web-proxy path; this warning still surfaces misconfigured direct API
    access and missing compose defaults.
    """
    if settings.COOKIE_SECURE is not None:
        return
    if settings.APP_ENV.lower() in {"development", "production"}:
        return
    if settings.cookie_secure_effective:
        logger.warning(
            "COOKIE_SECURE unset with APP_ENV=%s → Secure cookies by default. "
            "Plain HTTP origins (Tailscale without TLS) discard them and "
            "authenticated API calls return 401 'Could not validate credentials'. "
            "Set COOKIE_SECURE=false for HTTP homelab, or terminate TLS. "
            "When traffic goes through the web proxy, X-Forwarded-Proto=http "
            "disables Secure per request.",
            settings.APP_ENV,
        )
