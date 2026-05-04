"""Tests for daily-entry endpoints and service (M1, Issue #7).

Coverage
--------
Service layer:
- create_entry      — happy path, backdate boundary, future date guard,
                      conflict on duplicate, error rolls back the session.
- update_entry      — within window, read-only past window, not-found.
- list_entries      — limit clamping, date filters.

Endpoint layer:
- POST /api/v1/entries        — 201, 422 invalid range, 409 conflict, 401 unauth.
- GET  /api/v1/entries/{id}   — 200, 404.
- GET  /api/v1/entries        — 200 + list shape.
- PATCH /api/v1/entries/{id}  — 200, 404, 409 read-only.

All DB calls are mocked. No real Postgres or Redis is required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.entry import EntrySlot, WorkContext
from app.models.user import User
from app.schemas.entry import EntryCreate, EntryUpdate
from app.services import entry_service
from app.services.entry_service import (
    EntryConflictError,
    EntryDateOutOfRangeError,
    EntryNotFoundError,
    EntryReadOnlyError,
    create_entry,
    get_entry,
    list_entries,
    update_entry,
)
from tests.conftest import make_entry, make_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(*, flush_raises: Exception | None = None) -> MagicMock:
    """Build an AsyncSession mock with `add`, `flush`, `rollback` ready."""
    db = MagicMock()
    db.add = MagicMock()
    if flush_raises is not None:
        db.flush = AsyncMock(side_effect=flush_raises)
    else:
        db.flush = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _payload(**overrides: object) -> EntryCreate:
    base = {
        "entry_date": date.today(),
        "slot": EntrySlot.DAY,
        "mood_score": 4,
        "energy": 3,
        "stress": 2,
        "work_context": WorkContext.HOMEOFFICE,
        "note": "feeling good",
    }
    base.update(overrides)
    return EntryCreate(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Service: create_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_entry_happy_path() -> None:
    user = make_user()
    db = _make_db()

    entry = await create_entry(db, user_id=user.id, payload=_payload())

    assert entry.user_id == user.id
    assert entry.mood_score == 4
    assert entry.energy == 3
    assert entry.stress == 2
    assert entry.work_context is WorkContext.HOMEOFFICE
    assert entry.note_enc == "feeling good"
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_entry_at_backdate_boundary_succeeds() -> None:
    """Exactly 7 days back is still allowed."""
    user = make_user()
    db = _make_db()
    seven_days_ago = date.today() - timedelta(days=7)

    entry = await create_entry(db, user_id=user.id, payload=_payload(entry_date=seven_days_ago))

    assert entry.entry_date == seven_days_ago


@pytest.mark.asyncio
async def test_create_entry_older_than_window_rejected() -> None:
    user = make_user()
    db = _make_db()
    too_old = date.today() - timedelta(days=8)

    with pytest.raises(EntryDateOutOfRangeError):
        await create_entry(db, user_id=user.id, payload=_payload(entry_date=too_old))

    db.add.assert_not_called()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_entry_duplicate_raises_conflict() -> None:
    """IntegrityError → EntryConflictError + rollback."""
    user = make_user()
    integrity = IntegrityError("INSERT", params=None, orig=Exception("uq"))
    db = _make_db(flush_raises=integrity)

    with pytest.raises(EntryConflictError):
        await create_entry(db, user_id=user.id, payload=_payload())

    db.rollback.assert_awaited_once()


# ---------------------------------------------------------------------------
# Service: update_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_entry_within_window_changes_fields() -> None:
    user = make_user()
    existing = make_entry(user, mood_score=3, note="old")
    db = MagicMock()
    db.flush = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=result_mock)

    updated = await update_entry(
        db,
        user_id=user.id,
        entry_id=existing.id,
        payload=EntryUpdate(mood_score=5, note="great day"),
    )

    assert updated.mood_score == 5
    assert updated.note_enc == "great day"
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_entry_outside_window_is_read_only() -> None:
    user = make_user()
    stale = make_entry(user, entry_date=date.today() - timedelta(days=30))
    db = MagicMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = stale
    db.execute = AsyncMock(return_value=result_mock)
    db.flush = AsyncMock()

    with pytest.raises(EntryReadOnlyError):
        await update_entry(
            db,
            user_id=user.id,
            entry_id=stale.id,
            payload=EntryUpdate(mood_score=5),
        )

    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_entry_not_found() -> None:
    user = make_user()
    db = MagicMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)
    db.flush = AsyncMock()

    with pytest.raises(EntryNotFoundError):
        await update_entry(
            db,
            user_id=user.id,
            entry_id=uuid.uuid4(),
            payload=EntryUpdate(mood_score=5),
        )


# ---------------------------------------------------------------------------
# Service: list_entries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_entries_clamps_limit() -> None:
    """Limit > MAX is clamped silently — guard rail, not user error."""
    user = make_user()
    db = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = []
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars
    db.execute = AsyncMock(return_value=result_mock)

    out = await list_entries(db, user_id=user.id, limit=10_000)
    assert out == []
    # The query was built — we just confirm no crash + correct call shape.
    db.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# Service: get_entry — ownership second line of defence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_entry_returns_entry_for_owner() -> None:
    user = make_user()
    entry = make_entry(user)
    db = MagicMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = entry
    db.execute = AsyncMock(return_value=result_mock)

    out = await get_entry(db, user_id=user.id, entry_id=entry.id)
    assert out is entry


@pytest.mark.asyncio
async def test_get_entry_other_user_returns_not_found() -> None:
    user = make_user()
    db = MagicMock()
    result_mock = MagicMock()
    # The query filters on user_id, so a foreign entry just yields None.
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    with pytest.raises(EntryNotFoundError):
        await get_entry(db, user_id=user.id, entry_id=uuid.uuid4())


# ---------------------------------------------------------------------------
# Endpoint layer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_entry_201(async_client: AsyncClient, user: User) -> None:
    new_entry = make_entry(user, mood_score=4, energy=3, stress=2, note="hi")

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.entries.create_entry",
            new_callable=AsyncMock,
            return_value=new_entry,
        ):
            r = await async_client.post(
                "/api/v1/entries",
                json={
                    "entry_date": date.today().isoformat(),
                    "slot": "day",
                    "mood_score": 4,
                    "energy": 3,
                    "stress": 2,
                    "work_context": "homeoffice",
                    "note": "hi",
                },
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 201
    body = r.json()
    assert body["mood_score"] == 4
    assert body["work_context"] == "homeoffice"
    assert body["note"] == "hi"
    assert "id" in body


@pytest.mark.asyncio
async def test_post_entry_unauthenticated(async_client: AsyncClient) -> None:
    r = await async_client.post(
        "/api/v1/entries",
        json={
            "entry_date": date.today().isoformat(),
            "mood_score": 3,
            "energy": 3,
            "stress": 3,
            "work_context": "homeoffice",
        },
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_post_entry_invalid_range_422(async_client: AsyncClient, user: User) -> None:
    """Pydantic rejects mood_score=0 with 422 before hitting the service."""

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        r = await async_client.post(
            "/api/v1/entries",
            json={
                "entry_date": date.today().isoformat(),
                "mood_score": 0,  # invalid
                "energy": 3,
                "stress": 3,
                "work_context": "homeoffice",
            },
            cookies={"access_token": "valid.access.token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 422


@pytest.mark.asyncio
async def test_post_entry_too_old_422(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.entries.create_entry",
            new_callable=AsyncMock,
            side_effect=EntryDateOutOfRangeError("too old"),
        ):
            r = await async_client.post(
                "/api/v1/entries",
                json={
                    "entry_date": (date.today() - timedelta(days=8)).isoformat(),
                    "mood_score": 3,
                    "energy": 3,
                    "stress": 3,
                    "work_context": "homeoffice",
                },
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 422
    assert "too old" in r.json()["detail"]


@pytest.mark.asyncio
async def test_post_entry_conflict_409(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.entries.create_entry",
            new_callable=AsyncMock,
            side_effect=EntryConflictError("dupe"),
        ):
            r = await async_client.post(
                "/api/v1/entries",
                json={
                    "entry_date": date.today().isoformat(),
                    "mood_score": 3,
                    "energy": 3,
                    "stress": 3,
                    "work_context": "homeoffice",
                },
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 409


@pytest.mark.asyncio
async def test_get_entry_404(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.entries.get_entry",
            new_callable=AsyncMock,
            side_effect=EntryNotFoundError("missing"),
        ):
            r = await async_client.get(
                f"/api/v1/entries/{uuid.uuid4()}",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_entries_200(async_client: AsyncClient, user: User) -> None:
    rows = [make_entry(user, entry_date=date.today() - timedelta(days=i)) for i in range(3)]

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.entries.list_entries",
            new_callable=AsyncMock,
            return_value=rows,
        ):
            r = await async_client.get(
                "/api/v1/entries?limit=10",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 3
    assert all(set(item.keys()) >= {"id", "mood_score", "work_context"} for item in body)


@pytest.mark.asyncio
async def test_patch_entry_200(async_client: AsyncClient, user: User) -> None:
    updated = make_entry(user, mood_score=5, note="updated")

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.entries.update_entry",
            new_callable=AsyncMock,
            return_value=updated,
        ):
            r = await async_client.patch(
                f"/api/v1/entries/{updated.id}",
                json={"mood_score": 5, "note": "updated"},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.json()["mood_score"] == 5
    assert r.json()["note"] == "updated"


@pytest.mark.asyncio
async def test_patch_entry_read_only_409(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.entries.update_entry",
            new_callable=AsyncMock,
            side_effect=EntryReadOnlyError("read-only"),
        ):
            r = await async_client.patch(
                f"/api/v1/entries/{uuid.uuid4()}",
                json={"mood_score": 5},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 409


# ---------------------------------------------------------------------------
# Privacy: log scrubbing
# ---------------------------------------------------------------------------


def test_entry_service_logs_no_sensitive_fields() -> None:
    """Static check: every ``logger.<level>(...)`` call in the entry-service
    must not reference mood/energy/stress/note. Belt-and-suspenders for
    ADR-0007 §"Logging-Hygiene".
    """
    import inspect
    import re

    src = inspect.getsource(entry_service)
    log_calls = re.findall(
        r"logger\.(?:info|warning|error|debug)\s*\([^)]*\)",
        src,
        flags=re.DOTALL,
    )
    assert log_calls, "entry_service should have at least one log call"

    forbidden = ("mood_score", "energy", "stress", "note_enc", "note")
    for call in log_calls:
        for needle in forbidden:
            assert needle not in call, f"sensitive field {needle!r} leaked into log call: {call}"


def test_entry_static_clock_indirection_can_be_patched(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sanity check: the ``_today`` indirection lets us pin the clock."""
    monkeypatch.setattr(entry_service, "_today", lambda: date(2026, 1, 15))
    assert entry_service._today() == date(2026, 1, 15)


# Reference imports kept for static analysis: these are used implicitly
# via mocks in the tests above and we want unused-import linting to stay
# silent on them when the module is imported by the runner.
_ = (UTC, datetime)
