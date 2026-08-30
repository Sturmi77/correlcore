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
async def test_accepts_legacy_report_uri_shape(async_client: AsyncClient) -> None:
    body = json.dumps(
        {
            "csp-report": {
                "document-uri": "https://app.example.com/",
                "violated-directive": "script-src 'self'",
                "blocked-uri": "https://evil.example/x.js",
            }
        }
    )
    resp = await async_client.post(
        _CSP_REPORT,
        content=body.encode(),
        headers={"Content-Type": "application/csp-report"},
    )
    # 204, and crucially NOT 415 — the CSRF gate exempts this route+media type.
    assert resp.status_code == 204


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
