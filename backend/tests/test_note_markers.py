"""Unit tests for note marker normalisation and API surface."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.entry_note import EntryNoteMarker, NoteMarkerSource
from app.schemas.note import EntryNoteMarkerCreate
from app.services.note_markers import (
    NoteMarkerConflictError,
    NoteMarkerValidationError,
    add_marker_to_entry,
    aggregate_marker_summary,
    normalise_marker,
)
from tests.conftest import make_entry, make_user


def test_normalise_marker_lowercases_and_collapses_whitespace() -> None:
    assert normalise_marker("  Stress  ") == "stress"
    assert normalise_marker("Home Office") == "home office"


def test_normalise_marker_rejects_empty() -> None:
    with pytest.raises(NoteMarkerValidationError):
        normalise_marker("   ")


def test_normalise_marker_rejects_too_long_custom_marker() -> None:
    with pytest.raises(NoteMarkerValidationError):
        normalise_marker("x" * 40)


@pytest.mark.asyncio
async def test_add_marker_to_entry_normalises_key() -> None:
    user = make_user()
    entry = make_entry(user)
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=entry)))

    marker = await add_marker_to_entry(
        db,
        user_id=user.id,
        entry_id=entry.id,
        payload=EntryNoteMarkerCreate(marker="  Stress ", source=NoteMarkerSource.USER),
    )

    assert marker.marker == "stress"
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_aggregate_marker_summary_groups_by_marker() -> None:
    user = make_user()
    entry_a = make_entry(user, entry_date=date(2026, 7, 1), mood_score=2)
    entry_b = make_entry(user, entry_date=date(2026, 7, 2), mood_score=4)
    marker_a = EntryNoteMarker(
        id=uuid.uuid4(),
        entry_id=entry_a.id,
        user_id=user.id,
        marker="stress",
        source=NoteMarkerSource.USER,
    )
    marker_b = EntryNoteMarker(
        id=uuid.uuid4(),
        entry_id=entry_b.id,
        user_id=user.id,
        marker="stress",
        source=NoteMarkerSource.USER,
    )

    db = MagicMock()
    db.execute = AsyncMock(
        return_value=MagicMock(
            all=MagicMock(
                return_value=[
                    ("stress", entry_a.id, entry_a.mood_score),
                    ("stress", entry_b.id, entry_b.mood_score),
                ]
            )
        )
    )

    items = await aggregate_marker_summary(
        db,
        user_id=user.id,
        from_date=date(2026, 7, 1),
        to_date=date(2026, 7, 31),
    )

    assert len(items) == 1
    assert items[0].marker == "stress"
    assert items[0].count == 2
    assert items[0].avg_mood == 3.0
    assert marker_a.marker == "stress"
    assert marker_b.marker == "stress"


@pytest.mark.asyncio
async def test_create_note_marker_endpoint_returns_201(async_client: AsyncClient, user) -> None:
    entry = make_entry(user)
    marker = EntryNoteMarker(
        id=uuid.uuid4(),
        entry_id=entry.id,
        user_id=user.id,
        marker="work",
        source=NoteMarkerSource.USER,
        created_at=datetime.now(UTC),
    )

    app.dependency_overrides[get_current_verified_user] = lambda: user
    try:
        with patch(
            "app.api.v1.endpoints.note_markers.add_marker_to_entry",
            new_callable=AsyncMock,
            return_value=marker,
        ):
            response = await async_client.post(
                f"/api/v1/entries/{entry.id}/note-markers",
                json={"marker": "work", "source": "user"},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["marker"] == "work"


@pytest.mark.asyncio
async def test_marker_summary_endpoint(async_client: AsyncClient, user) -> None:
    app.dependency_overrides[get_current_verified_user] = lambda: user
    try:
        with patch(
            "app.api.v1.endpoints.analysis.aggregate_marker_summary",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = await async_client.get(
                "/api/v1/analysis/notes/marker-summary",
                params={"from": "2026-07-01", "to": "2026-07-31"},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["from"] == "2026-07-01"
    assert body["to"] == "2026-07-31"
    assert body["items"] == []


@pytest.mark.asyncio
async def test_add_marker_conflict_on_duplicate() -> None:
    user = make_user()
    entry = make_entry(user)
    db = MagicMock()
    db.add = MagicMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock(side_effect=IntegrityError("dup", {}, Exception()))
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=entry)))

    with pytest.raises(NoteMarkerConflictError):
        await add_marker_to_entry(
            db,
            user_id=user.id,
            entry_id=entry.id,
            payload=EntryNoteMarkerCreate(marker="work"),
        )
