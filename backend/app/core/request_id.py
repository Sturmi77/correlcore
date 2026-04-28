"""Request-ID / Correlation-ID middleware.

Every incoming HTTP request receives a ``request_id`` (UUID4).
- If the client sends ``X-Request-ID`` it is reused (preserves trace chains
  from Traefik or upstream callers).
- The id is stored in a contextvar so it flows into every log record
  (via ``app.core.logging.set_request_context``).
- The id is returned as ``X-Request-ID`` response header so callers can
  correlate their logs with the API logs.

Timing
------
``duration_ms`` is measured from the moment the middleware starts processing
until the response is ready to stream. It is written into the contextvar
after the inner call so that the access-log record emitted at the end of
``dispatch`` already contains the correct value.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import set_request_context

logger = logging.getLogger(__name__)

_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach / propagate a request-scoped correlation ID."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Reuse client-supplied ID or generate a new one
        request_id = request.headers.get(_HEADER) or str(uuid.uuid4())

        # Populate context — status_code / duration_ms filled in below
        set_request_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        t0 = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Update context with response data for the access log
        set_request_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        logger.info("request completed")

        # Propagate ID to caller
        response.headers[_HEADER] = request_id
        return response
