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
Exceptions are scoped to a specific ``(method, path)`` rather than allowed
globally (#791). ``multipart/form-data`` is a "simple" content type a cross-site
form can post without a preflight, so allowing it on *every* mutating route would
re-open form-CSRF on all of them if SameSite ever regresses. It is therefore
permitted only where a route genuinely needs it:

* ``POST /api/v1/media/photos`` — the authenticated photo upload needs
  ``multipart/form-data`` and is still protected by SameSite=strict + auth.
* ``POST /api/v1/security/csp-report`` — browsers deliver CSP violation reports
  as ``application/csp-report`` / ``application/reports+json`` (report-only CSP,
  audit S3 / #791). The endpoint is unauthenticated and side-effect-free.

Other rules
-----------
* Bodiless mutations (logout, refresh, account delete) send no body and no
  ``Content-Type`` and are allowed — there is no form payload to smuggle. An
  empty ``Content-Type`` is only treated as bodiless when the request actually
  has no body: a request that carries a body but omits the media type is
  rejected (#791), because a cross-origin ``fetch(url, {method: "POST",
  credentials: "include"})`` is CORS-safelisted (no preflight) and would
  otherwise slip through with an empty ``Content-Type``.
* Only state-changing methods are gated; ``GET``/``HEAD``/``OPTIONS`` (incl. the
  CORS preflight) pass through untouched.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Every mutating body must be JSON …
_JSON_MEDIA_TYPE = "application/json"

# … except on these exact ``(method, path)`` routes, which additionally accept
# the listed "simple"/report media types. Scoping the allowance to the route
# (rather than a global set) keeps the multipart form-CSRF vector closed on all
# other mutating endpoints (#791). Paths include the ``/api/v1`` router prefix,
# matching ``request.url.path`` before routing.
_ROUTE_MEDIA_EXCEPTIONS: dict[tuple[str, str], frozenset[str]] = {
    ("POST", "/api/v1/media/photos"): frozenset({"multipart/form-data"}),
    ("POST", "/api/v1/security/csp-report"): frozenset(
        {"application/csp-report", "application/reports+json"}
    ),
}


def _media_type(content_type: str) -> str:
    """Return the lowercased media type without parameters (``; charset=…``)."""

    return content_type.split(";", 1)[0].strip().lower()


def _request_has_body(request: Request) -> bool:
    """Best-effort: does this request carry a body?

    A chunked transfer or a positive ``Content-Length`` means a body is present.
    A malformed ``Content-Length`` is treated as "body present" — fail closed, an
    unparseable length is not a credible bodiless request.
    """

    if "chunked" in request.headers.get("transfer-encoding", "").lower():
        return True
    content_length = request.headers.get("content-length")
    if content_length is None:
        return False
    try:
        return int(content_length) > 0
    except ValueError:
        return True


def _allowed_media_types(method: str, path: str) -> frozenset[str]:
    """JSON, plus any route-scoped exceptions for this ``(method, path)``."""

    return frozenset({_JSON_MEDIA_TYPE}) | _ROUTE_MEDIA_EXCEPTIONS.get((method, path), frozenset())


class ContentTypeCSRFMiddleware(BaseHTTPMiddleware):
    """Reject state-changing requests whose body is not ``application/json``."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in _STATE_CHANGING_METHODS:
            media_type = _media_type(request.headers.get("content-type", ""))
            if media_type:
                if media_type not in _allowed_media_types(request.method, request.url.path):
                    return _reject(
                        "Unsupported Content-Type for a state-changing request; "
                        "use application/json."
                    )
            elif _request_has_body(request):
                # A body with no declared media type: a CORS-safelisted
                # cross-origin fetch can reach here without a preflight (#791).
                return _reject(
                    "A state-changing request with a body must declare a "
                    "Content-Type of application/json."
                )
        return await call_next(request)


def _reject(detail: str) -> JSONResponse:
    return JSONResponse(status_code=415, content={"detail": detail})
