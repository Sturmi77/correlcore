"""Shared auth-cookie helpers.

The auth and user routers both need to set or clear the same HttpOnly
cookies. Keeping names, paths, and security attributes in one module avoids
silent drift: a path change in the login flow must also affect logout,
refresh-error cleanup, and DSGVO account deletion.
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


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Attach access and refresh cookies with ADR-0004 security attributes."""
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path=ACCESS_COOKIE_PATH,
        max_age=ACCESS_COOKIE_MAX_AGE_SECONDS,
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
        max_age=REFRESH_COOKIE_MAX_AGE_SECONDS,
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear both auth cookies using the exact paths used when setting them."""
    response.delete_cookie(ACCESS_COOKIE_NAME, path=ACCESS_COOKIE_PATH)
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
