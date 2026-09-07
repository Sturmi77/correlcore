"""Tests for the Health Data Maturity service (Issue #852).

The three profile tests mirror the canonical fixtures in
``docs/features/health-data-maturity.md`` §9. Coverage/gate boundaries and the
Art. 9 no-leak guarantee (§8) are covered separately.
"""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.user import User
from app.schemas.stats import (
    CoverageMetric,
    HealthContextCoverage,
    HealthContextMaturity,
    HealthContextResponse,
    HealthContextSection,
)
from app.services.health_context_service import (
    HEALTH_CONTEXT_WINDOW_DAYS,
    get_health_context,
)

AS_OF = date(2026, 9, 7)


def _sample_dto() -> HealthContextResponse:
    return HealthContextResponse(
        as_of=AS_OF,
        coverage_window_days=90,
        maturity=HealthContextMaturity(
            phase="provisional",
            phase_index=3,
            current_entries=24,
            next_phase_at=30,
            entries_until_next=6,
        ),
        coverage=HealthContextCoverage(
            entry=CoverageMetric(days_with_data=22, window_days=90, pct=0.24),
            sleep=CoverageMetric(days_with_data=3, window_days=90, pct=0.03),
            symptom=CoverageMetric(days_with_data=16, window_days=90, pct=0.18),
        ),
        sections=[
            HealthContextSection(
                id="symptom",
                unlocked=True,
                reason="ok",
                entries_until_unlock=None,
                copy_key="trends.maturity.symptom.ok",
            ),
            HealthContextSection(
                id="sleep",
                unlocked=False,
                reason="insufficient_coverage",
                entries_until_unlock=None,
                copy_key="trends.maturity.sleep.insufficient_coverage",
            ),
        ],
        health_connect=None,
    )


def _scalar_one(value: int) -> MagicMock:
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _scalar_one_or_none(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _mock_db(
    *,
    entry_count: int,
    entry_days: int,
    sleep_days: int,
    symptom_days: int,
    consent: bool = False,
) -> MagicMock:
    """Wire an AsyncSession mock for the service's fixed query order.

    Order: maturity (all-history distinct days) -> entry-days -> sleep-days ->
    symptom-days -> Health-Connect consent lookup.
    """

    consent_row = MagicMock(granted=True) if consent else None
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one(entry_count),
            _scalar_one(entry_days),
            _scalar_one(sleep_days),
            _scalar_one(symptom_days),
            _scalar_one_or_none(consent_row),
        ]
    )
    return db


def _section(dto, section_id):  # type: ignore[no-untyped-def]
    return next(section for section in dto.sections if section.id == section_id)


@pytest.mark.asyncio
async def test_profile_new_all_sections_locked() -> None:
    # Fixture §9.1 — fresh account (< 7 entries): collecting phase, everything gated.
    db = _mock_db(entry_count=4, entry_days=4, sleep_days=2, symptom_days=1)

    dto = await get_health_context(db, user_id=uuid.uuid4(), as_of=AS_OF)

    assert dto.coverage_window_days == HEALTH_CONTEXT_WINDOW_DAYS == 90
    assert dto.maturity.phase == "collecting"
    assert dto.maturity.phase_index == 1
    assert dto.maturity.current_entries == 4
    assert dto.maturity.entries_until_next == 3
    assert dto.coverage.entry.pct == 0.04
    assert dto.coverage.sleep.pct == 0.02
    assert dto.coverage.symptom.pct == 0.01

    symptom = _section(dto, "symptom")
    assert symptom.unlocked is False
    assert symptom.reason == "insufficient_entries"
    assert symptom.entries_until_unlock == 11
    assert symptom.copy_key == "trends.maturity.symptom.insufficient_entries"

    sleep = _section(dto, "sleep")
    assert sleep.unlocked is False
    assert sleep.reason == "insufficient_coverage"

    assert dto.health_connect is None


@pytest.mark.asyncio
async def test_profile_sleep_arm_symptom_unlocked_sleep_gated() -> None:
    # Fixture §9.2 — enough entries to unlock symptoms, but sleep coverage too low.
    db = _mock_db(entry_count=24, entry_days=22, sleep_days=3, symptom_days=16)

    dto = await get_health_context(db, user_id=uuid.uuid4(), as_of=AS_OF)

    assert dto.maturity.phase == "provisional"
    assert dto.maturity.phase_index == 3
    assert dto.maturity.entries_until_next == 6
    assert dto.coverage.entry.pct == 0.24
    assert dto.coverage.sleep.pct == 0.03
    assert dto.coverage.symptom.pct == 0.18

    symptom = _section(dto, "symptom")
    assert symptom.unlocked is True
    assert symptom.reason == "ok"
    assert symptom.entries_until_unlock is None

    sleep = _section(dto, "sleep")
    assert sleep.unlocked is False
    assert sleep.reason == "insufficient_coverage"

    assert dto.health_connect is None


@pytest.mark.asyncio
async def test_profile_symptom_rich_all_unlocked_with_health_connect() -> None:
    # Fixture §9.3 — robust history, all sections unlocked, HC consent granted.
    db = _mock_db(entry_count=96, entry_days=82, sleep_days=58, symptom_days=75, consent=True)

    dto = await get_health_context(db, user_id=uuid.uuid4(), as_of=AS_OF)

    assert dto.maturity.phase == "robust"
    assert dto.maturity.phase_index == 4
    assert dto.maturity.next_phase_at is None
    assert dto.maturity.entries_until_next is None
    assert dto.coverage.entry.pct == 0.91
    assert dto.coverage.sleep.pct == 0.64
    assert dto.coverage.symptom.pct == 0.83

    assert _section(dto, "symptom").unlocked is True
    assert _section(dto, "sleep").unlocked is True

    assert dto.health_connect is not None
    assert dto.health_connect.consent is True
    # v1 exposes consent only — no import state source yet (spec D6).
    assert dto.health_connect.last_sync_at is None
    assert dto.health_connect.sleep_import_ok is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("entry_count", "expected_unlocked", "expected_until"),
    [(14, False, 1), (15, True, None)],
)
async def test_symptom_gate_boundary_at_15_entries(
    entry_count: int, expected_unlocked: bool, expected_until: int | None
) -> None:
    db = _mock_db(entry_count=entry_count, entry_days=entry_count, sleep_days=0, symptom_days=0)

    dto = await get_health_context(db, user_id=uuid.uuid4(), as_of=AS_OF)

    symptom = _section(dto, "symptom")
    assert symptom.unlocked is expected_unlocked
    assert symptom.entries_until_unlock == expected_until


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sleep_days", "expected_unlocked"),
    [
        (44, False),  # 44/90 = 0.49 -> below the 0.5 coverage gate
        (45, True),  # 45/90 = 0.50 -> meets coverage AND >= 15 observations
        (18, False),  # >= 15 observations but coverage 0.20 -> still gated
    ],
)
async def test_sleep_gate_boundary_coverage_and_observations(
    sleep_days: int, expected_unlocked: bool
) -> None:
    db = _mock_db(entry_count=90, entry_days=90, sleep_days=sleep_days, symptom_days=0)

    dto = await get_health_context(db, user_id=uuid.uuid4(), as_of=AS_OF)

    sleep = _section(dto, "sleep")
    assert sleep.unlocked is expected_unlocked
    if not expected_unlocked:
        assert sleep.reason == "insufficient_coverage"


@pytest.mark.asyncio
async def test_no_consent_yields_null_health_connect() -> None:
    db = _mock_db(entry_count=30, entry_days=30, sleep_days=30, symptom_days=30, consent=False)

    dto = await get_health_context(db, user_id=uuid.uuid4(), as_of=AS_OF)

    assert dto.health_connect is None


@pytest.mark.asyncio
async def test_response_carries_only_counts_no_art9_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Privacy guard (spec §8): the DTO only ever holds counts/ratios/enums —
    # never plaintext symptom names or concrete sleep values — and the service
    # emits no logs that could leak them.
    db = _mock_db(entry_count=96, entry_days=82, sleep_days=58, symptom_days=75, consent=True)

    with caplog.at_level("DEBUG"):
        dto = await get_health_context(db, user_id=uuid.uuid4(), as_of=AS_OF)

    payload = dto.model_dump()
    assert set(payload["coverage"]["sleep"].keys()) == {"days_with_data", "window_days", "pct"}
    # Coverage values are ratios in [0, 1], never raw sleep minutes/quality.
    for metric in payload["coverage"].values():
        assert 0.0 <= metric["pct"] <= 1.0
    # Sections expose only ids/flags/copy-keys, no free-text health content.
    for section in payload["sections"]:
        assert set(section.keys()) == {
            "id",
            "unlocked",
            "reason",
            "entries_until_unlock",
            "copy_key",
        }
    assert caplog.records == []


@pytest.mark.asyncio
async def test_health_context_endpoint_returns_dto(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.entries.get_health_context",
            new_callable=AsyncMock,
            return_value=_sample_dto(),
        ):
            r = await async_client.get(
                "/api/v1/entries/stats/health-context",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert body["coverage_window_days"] == 90
    assert body["maturity"]["phase"] == "provisional"
    assert {s["id"] for s in body["sections"]} == {"symptom", "sleep"}
    assert body["health_connect"] is None


@pytest.mark.asyncio
async def test_health_context_endpoint_unauthenticated(async_client: AsyncClient) -> None:
    r = await async_client.get("/api/v1/entries/stats/health-context")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_health_context_endpoint_contract_shape(
    async_client: AsyncClient, user: User
) -> None:
    # Drift guard: the serialized JSON must match the frontend
    # `HealthContextResponse` interface (apps/web/src/lib/api/stats.ts).
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.entries.get_health_context",
            new_callable=AsyncMock,
            return_value=_sample_dto(),
        ):
            r = await async_client.get(
                "/api/v1/entries/stats/health-context",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    body = r.json()
    assert set(body.keys()) == {
        "as_of",
        "coverage_window_days",
        "maturity",
        "coverage",
        "sections",
        "health_connect",
    }
    assert set(body["maturity"].keys()) == {
        "phase",
        "phase_index",
        "current_entries",
        "next_phase_at",
        "entries_until_next",
    }
    assert set(body["coverage"].keys()) == {"entry", "sleep", "symptom"}
    for metric in body["coverage"].values():
        assert set(metric.keys()) == {"days_with_data", "window_days", "pct"}
    for section in body["sections"]:
        assert set(section.keys()) == {
            "id",
            "unlocked",
            "reason",
            "entries_until_unlock",
            "copy_key",
        }
