#!/usr/bin/env python3
"""Verify M7 analytics endpoints after ``seed_m7_qa.py`` against a running API.

Usage::

    cd backend
    uv run --python 3.12 python scripts/seed_m7_qa.py --reset
    # API at http://127.0.0.1:8000
    uv run --python 3.12 python scripts/verify_m7_qa_api.py

Exits 0 when login, insights, tag-clusters, and symptom co-occurrence all succeed.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import httpx

from app.services.m7_qa_seed_service import M7_QA_DEFAULT_EMAIL, M7_QA_DEFAULT_PASSWORD

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify M7 QA API responses")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--email", default=M7_QA_DEFAULT_EMAIL)
    parser.add_argument("--password", default=M7_QA_DEFAULT_PASSWORD)
    return parser.parse_args()


async def _main() -> int:
    args = _parse_args()
    base = args.base_url.rstrip("/")

    async with httpx.AsyncClient(base_url=base, timeout=30.0) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": args.email, "password": args.password},
        )
        if login.status_code != 200:
            print(f"login failed: {login.status_code} {login.text}")
            return 1

        token = login.json().get("access_token")
        if not token:
            print("login response missing access_token")
            return 1

        headers = {"Authorization": f"Bearer {token}"}
        insights = await client.get(
            "/api/v1/insights/latest", headers=headers, params={"limit": 50}
        )
        clusters = await client.get("/api/v1/insights/tag-clusters", headers=headers)
        cooccurrence = await client.get(
            "/api/v1/insights/symptom-tag-cooccurrence",
            params={"range": "90d"},
            headers=headers,
        )

        checks = [
            ("insights/latest", insights, 200),
            ("insights/tag-clusters", clusters, 200),
            ("insights/symptom-tag-cooccurrence", cooccurrence, 200),
        ]
        failed = False
        for name, response, expected in checks:
            if response.status_code != expected:
                print(f"{name}: expected {expected}, got {response.status_code}")
                failed = True
                continue
            print(f"{name}: ok")

        insight_payload = insights.json()
        insight_items = insight_payload.get("insights") or []
        insight_types = {
            item.get("insight_type") for item in insight_items if isinstance(item, dict)
        }
        if "symptom_cluster" not in insight_types:
            print(f"symptom_cluster missing from latest insights: {sorted(insight_types)}")
            failed = True
        else:
            print("symptom_cluster present in latest insights")

        cluster_payload = clusters.json()
        if cluster_payload.get("status") != "ok":
            print(f"tag-clusters status: {cluster_payload.get('status')}")
            failed = True
        else:
            print(f"tag-clusters: {len(cluster_payload.get('clusters', []))} groups")

        cooccurrence_cells = cooccurrence.json().get("cells", [])
        if not cooccurrence_cells:
            print("symptom-tag-cooccurrence returned no cells")
            failed = True
        else:
            print(f"symptom-tag-cooccurrence: {len(cooccurrence_cells)} cells")

        maturity_phase = insight_payload.get("insight_maturity", {}).get("phase")
        print(f"insight maturity phase: {maturity_phase}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
