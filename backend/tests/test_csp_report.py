"""Tests for the CSP violation-report collector (audit S3 / #791).

The endpoint is the report-only CSP's reporting destination: unauthenticated,
side-effect-free (logs only), and CSRF-exempt for the browser report media
types. It must never error on malformed input — a collector that 500s would lose
the very reports it exists to gather.
"""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient

_CSP_REPORT = "/api/v1/security/csp-report"


@pytest.mark.asyncio
async def test_accepts_legacy_report_uri_shape(
    async_client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    body = json.dumps(
        {
            "csp-report": {
                "document-uri": "https://app.example.com/",
                "violated-directive": "script-src 'self'",
                "blocked-uri": "https://evil.example/x.js",
            }
        }
    )
    with caplog.at_level("WARNING"):
        resp = await async_client.post(
            _CSP_REPORT,
            content=body.encode(),
            headers={"Content-Type": "application/csp-report"},
        )
    # 204, and crucially NOT 415 — the CSRF gate exempts this route+media type.
    assert resp.status_code == 204
    # The violation detail is actually recorded in the log message (the JSON
    # formatter serializes only the message, not extras), and control chars in
    # attacker-controlled fields are escaped via %r.
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "csp_violation" in logged
    assert "https://evil.example/x.js" in logged


@pytest.mark.asyncio
async def test_log_message_escapes_newlines_in_report_fields(
    async_client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    """A newline in an attacker-controlled field must not forge a second log line."""
    body = json.dumps({"csp-report": {"blocked-uri": "https://evil.example/\nFAKE level=CRITICAL"}})
    with caplog.at_level("WARNING"):
        resp = await async_client.post(
            _CSP_REPORT,
            content=body.encode(),
            headers={"Content-Type": "application/csp-report"},
        )
    assert resp.status_code == 204
    # %r renders the newline as an escape sequence, so the raw message carries no
    # literal newline from the report value.
    csp_records = [r for r in caplog.records if r.getMessage().startswith("csp_violation")]
    assert csp_records
    assert "\\n" in csp_records[0].getMessage()
    assert "\nFAKE level=CRITICAL" not in csp_records[0].getMessage()


@pytest.mark.asyncio
async def test_accepts_reporting_api_shape(async_client: AsyncClient) -> None:
    body = json.dumps(
        [
            {
                "type": "csp-violation",
                "body": {
                    "documentURL": "https://app.example.com/",
                    "effectiveDirective": "img-src",
                    "blockedURL": "https://evil.example/x.png",
                },
            }
        ]
    )
    resp = await async_client.post(
        _CSP_REPORT,
        content=body.encode(),
        headers={"Content-Type": "application/reports+json"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_malformed_body_still_204(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        _CSP_REPORT,
        content=b"not json at all",
        headers={"Content-Type": "application/csp-report"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_report_route_rejects_plain_text(async_client: AsyncClient) -> None:
    """The CSRF exemption is scoped to report media types, not text/plain."""
    resp = await async_client.post(
        _CSP_REPORT,
        content=b"{}",
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 415
