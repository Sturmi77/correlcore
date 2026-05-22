"""Shared SlowAPI Limiter - single source of truth for rate-limiting.

Endpoint modules import :data:`limiter` from here; :mod:`app.main` imports it
once and binds it to ``app.state.limiter``.
"""

from __future__ import annotations

from slowapi import Limiter
from starlette.requests import Request

from app.core.config import settings


def _client_host(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def rate_limit_key(request: Request) -> str:
    """Return the rate-limit bucket key for a request.

    By default we use the TCP peer address, which is spoof-resistant for
    directly exposed API ports. Deployments with a trusted reverse proxy can
    opt in to ``X-Forwarded-For`` handling. When enabled, the last non-empty
    address is used so a client-supplied left-most spoof does not win if the
    proxy appends the real peer address.
    """

    if settings.RATE_LIMIT_TRUST_PROXY_HEADERS:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        forwarded_hosts = [part.strip() for part in forwarded_for.split(",") if part.strip()]
        if forwarded_hosts:
            return forwarded_hosts[-1]

        real_ip = request.headers.get("x-real-ip", "").strip()
        if real_ip:
            return real_ip

    return _client_host(request)


def _rate_limit_storage_uri() -> str:
    if settings.APP_ENV.lower() == "test" and not settings.RATE_LIMIT_STORAGE_URL:
        return "memory://"
    return settings.RATE_LIMIT_STORAGE_URL or settings.REDIS_URL or "memory://"


#: Process-wide Limiter instance. Do **not** create a second one.
limiter = Limiter(key_func=rate_limit_key, storage_uri=_rate_limit_storage_uri())
