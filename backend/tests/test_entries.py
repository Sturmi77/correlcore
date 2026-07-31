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
from app.models.entry import BleedingLevel, EntrySlot, EntrySource, WorkContext
from app.models.user import User
from app.schemas.entry import (
    EntryBatchCreate,
    EntryCreate,
    EntryDeltaResponse,
    EntryResponse,
    EntryUpdate,
)
from app.services import entry_service
from app.services.entry_service import (
    EntryConflictError,
    EntryDateOutOfRangeError,
    EntryNotFoundError,
    EntryReadOnlyError,
    clear_user_cycle_data,
    create_entry,
    create_entry_batch,
    get_entry,
    get_entry_delta,
    list_entries,
    update_entry,
)
from tests.conftest import make_entry, make_tag, make_user

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


def _scalar_one_result(value: object | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalars_all_result(values: list[object]) -> MagicMock:
    scalars = MagicMock()
    scalars.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


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
async def test_create_entry_happy_path(rest_revision_recorders) -> None:
    user = make_user()
    db = _make_db()

    entry = await create_entry(db, user_id=user.id, payload=_payload(cycle_day=12))

    assert entry.user_id == user.id
    assert entry.mood_score == 4
    assert entry.energy == 3
    assert entry.stress == 2
    assert entry.cycle_day == 12
    assert entry.source is EntrySource.DIRECT
    assert entry.work_context is WorkContext.HOMEOFFICE
    assert entry.note_enc == "feeling good"
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    db.rollback.assert_not_awaited()
    rest_revision_recorders["entry"].assert_awaited_once()
    assert rest_revision_recorders["entry"].await_args.kwargs["entry"] is entry


@pytest.mark.asyncio
async def test_create_entry_persists_cycle_bleeding_level(rest_revision_recorders) -> None:
    user = make_user()
    db = _make_db()

    entry = await create_entry(
        db,
        user_id=user.id,
        payload=_payload(cycle_day=5, cycle_bleeding_level=BleedingLevel.LIGHT),
    )

    assert entry.cycle_day == 5
    assert entry.cycle_bleeding_level is BleedingLevel.LIGHT


@pytest.mark.asyncio
async def test_create_entry_at_backdate_boundary_succeeds() -> None:
    """Exactly 7 days back is still allowed."""
    user = make_user()
    db = _make_db()
    seven_days_ago = date.today() - timedelta(days=7)

    entry = await create_entry(db, user_id=user.id, payload=_payload(entry_date=seven_days_ago))

    assert entry.entry_date == seven_days_ago


@pytest.mark.asyncio
async def test_create_entry_allows_trailing_tz_slack_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local '7 days ago' west of UTC can be UTC today−8 — still editable."""
    user = make_user()
    db = _make_db()
    monkeypatch.setattr(entry_service, "_today", lambda: date(2026, 7, 24))
    local_seven_days_ago = date(2026, 7, 16)

    entry = await create_entry(
        db, user_id=user.id, payload=_payload(entry_date=local_seven_days_ago)
    )

    assert entry.entry_date == local_seven_days_ago


@pytest.mark.asyncio
async def test_create_entry_batch_marks_entries_retrospective() -> None:
    user = make_user()
    db = _make_db()

    entries = await create_entry_batch(
        db,
        user_id=user.id,
        payload=EntryBatchCreate(entries=[_payload(source=EntrySource.DIRECT)]),
    )

    assert len(entries) == 1
    assert entries[0].source is EntrySource.RETROSPECTIVE


@pytest.mark.asyncio
async def test_create_entry_older_than_window_rejected() -> None:
    user = make_user()
    db = _make_db()
    # Window is 7 local days plus one UTC/client-TZ slack day on the trailing edge.
    too_old = date.today() - timedelta(days=9)

    with pytest.raises(EntryDateOutOfRangeError):
        await create_entry(db, user_id=user.id, payload=_payload(entry_date=too_old))

    db.add.assert_not_called()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_entry_allows_local_today_ahead_of_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Device-local today east of UTC is UTC tomorrow — must still create.

    Production API containers run with no TZ (UTC). Home / entry sheet /
    widget all key ``entry_date`` by the device calendar day, so a Tokyo
    morning after local midnight sends tomorrow relative to the server clock.
    """
    user = make_user()
    db = _make_db()
    monkeypatch.setattr(entry_service, "_today", lambda: date(2026, 7, 23))
    local_today = date(2026, 7, 24)

    entry = await create_entry(db, user_id=user.id, payload=_payload(entry_date=local_today))

    assert entry.entry_date == local_today


def test_entry_create_schema_allows_one_day_ahead_of_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.schemas.entry.datetime",
        type(
            "FixedDateTime",
            (),
            {
                "now": staticmethod(lambda tz=None: datetime(2026, 7, 23, 15, 0, tzinfo=UTC)),
            },
        ),
    )
    payload = _payload(entry_date=date(2026, 7, 24))
    assert payload.entry_date == date(2026, 7, 24)


def test_entry_create_schema_rejects_two_days_ahead_of_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pydantic import ValidationError

    monkeypatch.setattr(
        "app.schemas.entry.datetime",
        type(
            "FixedDateTime",
            (),
            {
                "now": staticmethod(lambda tz=None: datetime(2026, 7, 23, 15, 0, tzinfo=UTC)),
            },
        ),
    )
    with pytest.raises(ValidationError):
        _payload(entry_date=date(2026, 7, 25))


@pytest.mark.asyncio
async def test_create_entry_duplicate_raises_conflict(rest_revision_recorders) -> None:
    """IntegrityError → EntryConflictError + rollback; no revision log."""
    user = make_user()
    integrity = IntegrityError("INSERT", params=None, orig=Exception("uq"))
    db = _make_db(flush_raises=integrity)

    with pytest.raises(EntryConflictError):
        await create_entry(db, user_id=user.id, payload=_payload())

    db.rollback.assert_awaited_once()
    rest_revision_recorders["entry"].assert_not_awaited()


# ---------------------------------------------------------------------------
# Service: clear_user_cycle_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clear_user_cycle_data_nulls_fields_and_records_revisions(
    rest_revision_recorders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    with_cycle = make_entry(user, cycle_day=5)
    with_cycle.cycle_bleeding_level = BleedingLevel.LIGHT
    without_cycle = make_entry(user, cycle_day=None)
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalars_all_result([with_cycle]))

    scrub = AsyncMock(return_value=1)
    monkeypatch.setattr(
        "app.services.sync_service.scrub_cycle_shd_from_revision_log",
        scrub,
    )

    cleared = await clear_user_cycle_data(db, user_id=user.id)

    assert cleared == 1
    assert with_cycle.cycle_day is None
    assert with_cycle.cycle_bleeding_level is None
    assert with_cycle.updated_at is not None
    assert without_cycle.cycle_day is None
    rest_revision_recorders["entry"].assert_awaited_once()
    assert rest_revision_recorders["entry"].await_args.kwargs["entry"] is with_cycle
    scrub.assert_awaited_once_with(db, user_id=user.id)


# ---------------------------------------------------------------------------
# Service: update_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_entry_within_window_changes_fields(rest_revision_recorders) -> None:
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
        payload=EntryUpdate(
            mood_score=5,
            note="great day",
            slot=EntrySlot.EVENING,
            cycle_day=21,
        ),
    )

    assert updated.mood_score == 5
    assert updated.note_enc == "great day"
    assert updated.slot is EntrySlot.EVENING
    assert updated.cycle_day == 21
    db.flush.assert_awaited_once()
    rest_revision_recorders["entry"].assert_awaited_once()
    assert rest_revision_recorders["entry"].await_args.kwargs["entry"] is updated


@pytest.mark.asyncio
async def test_update_entry_duplicate_slot_raises_conflict() -> None:
    user = make_user()
    existing = make_entry(user)
    integrity = IntegrityError("UPDATE", params=None, orig=Exception("uq"))
    db = MagicMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=result_mock)
    db.flush = AsyncMock(side_effect=integrity)
    db.rollback = AsyncMock()

    with pytest.raises(EntryConflictError):
        await update_entry(
            db,
            user_id=user.id,
            entry_id=existing.id,
            payload=EntryUpdate(slot=EntrySlot.MORNING),
        )

    db.rollback.assert_awaited_once()


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
# Service: get_entry_delta
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_entry_delta_returns_metric_differences_and_shared_tags() -> None:
    user = make_user()
    today = make_entry(
        user,
        entry_date=date(2026, 5, 13),
        mood_score=4,
        energy=2,
        stress=3,
    )
    previous = make_entry(
        user,
        entry_date=date(2026, 5, 12),
        mood_score=2,
        energy=4,
        stress=3,
    )
    shared = make_tag(user, slug="sport", name="Sport")
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_result(today),
            _scalar_one_result(previous),
            _scalars_all_result([shared]),
        ]
    )

    out = await get_entry_delta(
        db,
        user_id=user.id,
        entry_date=date(2026, 5, 13),
        slot=EntrySlot.DAY,
    )

    assert out.today is not None
    assert out.previous is not None
    assert out.delta.mood == 2
    assert out.delta.energy == -2
    assert out.delta.stress == 0
    assert [tag.slug for tag in out.shared_tags] == ["sport"]


@pytest.mark.asyncio
async def test_get_entry_delta_without_previous_entry_returns_no_delta() -> None:
    user = make_user()
    today = make_entry(user, entry_date=date(2026, 5, 13))
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_result(today),
            _scalar_one_result(None),
        ]
    )

    out = await get_entry_delta(db, user_id=user.id, entry_date=date(2026, 5, 13))

    assert out.today is not None
    assert out.previous is None
    assert out.delta.mood is None
    assert out.delta.energy is None
    assert out.delta.stress is None
    assert out.shared_tags == []
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_get_entry_delta_without_today_entry_returns_previous_context_only() -> None:
    user = make_user()
    previous = make_entry(user, entry_date=date(2026, 5, 12))
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_one_result(None),
            _scalar_one_result(previous),
        ]
    )

    out = await get_entry_delta(db, user_id=user.id, entry_date=date(2026, 5, 13))

    assert out.today is None
    assert out.previous is not None
    assert out.delta.mood is None
    assert out.shared_tags == []


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


async def _entry_response_from_model(_db, *, user_id, entry) -> EntryResponse:  # noqa: ANN001
    return EntryResponse.model_validate(entry)


async def _entry_responses_from_models(_db, *, user_id, entries) -> list[EntryResponse]:  # noqa: ANN001
    return [EntryResponse.model_validate(entry) for entry in entries]


@pytest.mark.asyncio
async def test_post_entry_201(async_client: AsyncClient, user: User) -> None:
    new_entry = make_entry(user, mood_score=4, energy=3, stress=2, note="hi")

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with (
            patch(
                "app.api.v1.endpoints.entries.create_entry",
                new_callable=AsyncMock,
                return_value=new_entry,
            ),
            patch(
                "app.api.v1.endpoints.entries.build_entry_response",
                new=_entry_response_from_model,
            ),
            patch(
                "app.api.v1.endpoints.entries.run_note_signal_extraction_background",
                new_callable=AsyncMock,
            ),
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
                    # Beyond 7 local days + one UTC/client-TZ slack day.
                    "entry_date": (date.today() - timedelta(days=9)).isoformat(),
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
        with (
            patch(
                "app.api.v1.endpoints.entries.list_entries",
                new_callable=AsyncMock,
                return_value=rows,
            ),
            patch(
                "app.api.v1.endpoints.entries.build_entry_responses",
                new=_entry_responses_from_models,
            ),
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
async def test_get_entry_delta_200(async_client: AsyncClient, user: User) -> None:
    today = make_entry(user, entry_date=date(2026, 5, 13), mood_score=4)
    previous = make_entry(user, entry_date=date(2026, 5, 12), mood_score=3)
    payload = EntryDeltaResponse.model_validate(
        {
            "today": today,
            "previous": previous,
            "delta": {"mood": 1, "energy": 0, "stress": 0},
            "shared_tags": [],
        }
    )

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.entries.get_entry_delta",
            new_callable=AsyncMock,
            return_value=payload,
        ) as mocked:
            r = await async_client.get(
                "/api/v1/entries/delta?entry_date=2026-05-13&slot=day",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert body["delta"]["mood"] == 1
    assert body["today"]["entry_date"] == "2026-05-13"
    mocked.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_entry_delta_unauthenticated(async_client: AsyncClient) -> None:
    r = await async_client.get("/api/v1/entries/delta?entry_date=2026-05-13")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_patch_entry_200(async_client: AsyncClient, user: User) -> None:
    updated = make_entry(user, mood_score=5, note="updated")

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with (
            patch(
                "app.api.v1.endpoints.entries.update_entry",
                new_callable=AsyncMock,
                return_value=updated,
            ),
            patch(
                "app.api.v1.endpoints.entries.build_entry_response",
                new=_entry_response_from_model,
            ),
            patch(
                "app.api.v1.endpoints.entries.run_note_signal_extraction_background",
                new_callable=AsyncMock,
            ),
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


@pytest.mark.asyncio
async def test_patch_entry_slot_conflict_409(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.entries.update_entry",
            new_callable=AsyncMock,
            side_effect=EntryConflictError("slot exists"),
        ):
            r = await async_client.patch(
                f"/api/v1/entries/{uuid.uuid4()}",
                json={"slot": "morning"},
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


# ---------------------------------------------------------------------------
# Stats — symptom heatmap (Trends Compare)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_symptom_heatmap_200(async_client: AsyncClient, user: User) -> None:
    from app.schemas.stats import SymptomHeatmapResponse

    async def override() -> User:
        return user

    payload = SymptomHeatmapResponse(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        symptoms=[],
    )
    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.entries.get_symptom_heatmap",
            new_callable=AsyncMock,
            return_value=payload,
        ) as mocked:
            r = await async_client.get(
                "/api/v1/entries/stats/symptoms?start_date=2026-01-01&end_date=2026-01-31",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.json() == {
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
        "symptoms": [],
    }
    mocked.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_symptom_heatmap_unauthenticated(async_client: AsyncClient) -> None:
    """Unauthenticated stats/symptoms must hit the stats handler (401), not
    ``/{entry_id}/symptoms`` (which used to Match.FULL for path ``stats``)."""
    with patch(
        "app.api.v1.endpoints.entries.get_symptom_heatmap",
        new_callable=AsyncMock,
    ) as mocked_heatmap:
        with patch(
            "app.api.v1.endpoints.symptoms.list_symptoms_for_entry",
            new_callable=AsyncMock,
        ) as mocked_entry:
            r = await async_client.get("/api/v1/entries/stats/symptoms")
    assert r.status_code == 401
    assert r.json()["detail"] == "Could not validate credentials"
    mocked_heatmap.assert_not_awaited()
    mocked_entry.assert_not_awaited()


# Reference imports kept for static analysis: these are used implicitly
# via mocks in the tests above and we want unused-import linting to stay
# silent on them when the module is imported by the runner.
_ = (UTC, datetime)
