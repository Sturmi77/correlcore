"""Unit tests for note marker normalisation and API surface."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
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
