"""Content-Type CSRF hardening middleware (audit M12, ADR-0006).

``SameSite=strict`` cookies are the primary CSRF control. This middleware adds
the belt-and-suspenders check ADR-0006 already promised ("JSON Content-Type
enforcement") but that was never enforced in the API: a state-changing request
that carries a body must declare ``application/json``.

A cross-site HTML ``<form>`` can only send the three "simple" content types
(``application/x-www-form-urlencoded``, ``text/plain``, ``multipart/form-data``)
and never sets a custom header without triggering a CORS preflight. Rejecting a
non-JSON body therefore blocks the classic form-based CSRF vector even if the
SameSite guarantee ever regresses (browser bug, proxy rewrite, config drift).

Exceptions
----------
* ``multipart/form-data`` is the one documented allowed type: the authenticated
  photo upload (``POST /api/v1/media/photos``) needs it and is still protected
  by SameSite=strict + auth. It is a "simple" type, so this is an accepted,
  documented residual rather than a new hole.
* Bodiless mutations (logout, refresh, account delete) send no ``Content-Type``
  and are allowed — there is no form payload to smuggle.
* Only state-changing methods are gated; ``GET``/``HEAD``/``OPTIONS`` (incl. the
  CORS preflight) pass through untouched.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# ``multipart/form-data`` is a documented exception for authenticated media
# uploads; every other mutating body must be JSON.
_ALLOWED_MEDIA_TYPES = frozenset({"application/json", "multipart/form-data"})


def _media_type(content_type: str) -> str:
    """Return the lowercased media type without parameters (``; charset=…``)."""

    return content_type.split(";", 1)[0].strip().lower()


class ContentTypeCSRFMiddleware(BaseHTTPMiddleware):
    """Reject state-changing requests whose body is not ``application/json``."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in _STATE_CHANGING_METHODS:
            media_type = _media_type(request.headers.get("content-type", ""))
            # An empty media type means no request body (bodiless POST/DELETE
            # such as logout/refresh) — nothing to smuggle, so allow it.
            if media_type and media_type not in _ALLOWED_MEDIA_TYPES:
                return JSONResponse(
                    status_code=415,
                    content={
                        "detail": (
                            "Unsupported Content-Type for a state-changing request; "
                            "use application/json."
                        )
                    },
                )
        return await call_next(request)
