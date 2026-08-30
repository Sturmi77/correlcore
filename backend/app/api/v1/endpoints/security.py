"""Security reporting collector (audit S3 / #791).

The deployment ships a ``Content-Security-Policy-Report-Only`` header (infra
Traefik stack) so violations can be observed before the policy is switched to
enforcing. Without a reporting destination the browser emits nothing, so the
"observe first" window collects no data. This endpoint is that destination: it
ingests CSP violation reports and logs them, giving a fully self-hosted,
observable path (no third-party report collector required).

The route is intentionally:

* **unauthenticated** — the browser posts violation reports without credentials,
  often for the anonymous landing page before any login;
* **side-effect-free** — it only logs; it never writes user data or returns a
  body, so there is nothing for a forged request to abuse;
* **CSRF-exempt for report media types** — browsers send ``application/csp-report``
  (legacy ``report-uri``) or ``application/reports+json`` (Reporting API), which
  the Content-Type CSRF gate allows only for this exact route (see
  ``app.core.csrf``).

It is excluded from the OpenAPI schema (``include_in_schema=False``): it is a
browser-to-infra hook, not part of the client API contract.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Request, Response, status

from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Bound the body we accept (DoS guard) and, separately and more tightly, what we
# log per field. The size cap is on the *raw body* and gates whether we parse at
# all — never a slice of the JSON before parsing, which would corrupt an
# otherwise valid large batch and drop exactly the bursts worth investigating.
# Report fields are attacker-controlled, so they are logged via ``%r`` (which
# escapes control characters) inside a message that the JSON log formatter then
# escapes again — no newline in a report value can forge a second log line.
_MAX_REPORT_BODY_BYTES = 64_000
_MAX_FIELD_LOG_CHARS = 300


def _truncate(value: object, limit: int = _MAX_FIELD_LOG_CHARS) -> str | None:
    """Stringify and length-cap an attacker-controlled field for logging."""

    if value is None:
        return None
    return str(value)[:limit]


def _summarize(payload: Any) -> list[dict[str, Any]]:
    """Extract the interesting fields from either report shape.

    ``report-uri`` posts ``{"csp-report": {...}}``; the Reporting API posts a
    list of ``{"type": "csp-violation", "body": {...}}`` entries. Returns a list
    of flat dicts with the fields worth alerting on; unknown shapes yield ``[]``.
    """

    reports: list[dict[str, Any]] = []
    if isinstance(payload, dict) and isinstance(payload.get("csp-report"), dict):
        reports.append(payload["csp-report"])
    elif isinstance(payload, list):
        for entry in payload:
            if isinstance(entry, dict) and isinstance(entry.get("body"), dict):
                reports.append(entry["body"])

    summaries: list[dict[str, Any]] = []
    for report in reports:
        summaries.append(
            {
                # Field names differ between the two schemas; check both.
                "directive": report.get("violated-directive")
                or report.get("effectiveDirective")
                or report.get("effective-directive"),
                "blocked_uri": report.get("blocked-uri") or report.get("blockedURL"),
                "document_uri": report.get("document-uri") or report.get("documentURL"),
            }
        )
    return summaries


@router.post(
    "/csp-report",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
@limiter.limit("60/minute")
async def csp_report(request: Request) -> Response:
    """Ingest a CSP violation report and log it. Always returns 204."""

    # Reject an oversized report by its declared Content-Length *before* buffering
    # the body, so an honestly-declared large POST never gets read into memory.
    declared_length = request.headers.get("content-length")
    if declared_length is not None:
        try:
            if int(declared_length) > _MAX_REPORT_BODY_BYTES:
                logger.warning("csp_report_oversized bytes=%s", declared_length)
                return Response(status_code=status.HTTP_204_NO_CONTENT)
        except ValueError:
            pass  # malformed header — fall through to the post-read guard below

    raw = await request.body()
    if len(raw) > _MAX_REPORT_BODY_BYTES:
        # Chunked / no Content-Length fallback: bound after reading, still never
        # parse a slice (truncating JSON before parsing corrupts it).
        logger.warning("csp_report_oversized bytes=%d", len(raw))
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Parse the *full* body (bounded above); only individual fields are truncated,
    # and only when logged.
    text = raw.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text) if text else None
    except json.JSONDecodeError:
        payload = None

    # The JSON log formatter (app.core.logging) serializes only the record's
    # message, not `extra=` fields, so the violation details are encoded into the
    # message itself (via %r) rather than passed as extras.
    summaries = _summarize(payload)
    if summaries:
        for summary in summaries:
            logger.warning(
                "csp_violation directive=%r blocked_uri=%r document_uri=%r",
                _truncate(summary["directive"]),
                _truncate(summary["blocked_uri"]),
                _truncate(summary["document_uri"]),
            )
    else:
        # Unrecognized shape — still record that something arrived, truncated.
        logger.warning("csp_report_unparsed raw=%r", _truncate(text))

    return Response(status_code=status.HTTP_204_NO_CONTENT)
