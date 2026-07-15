"""Note marker endpoints mounted under ``/entries``."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.note import EntryNoteMarkerCreate, EntryNoteMarkerResponse
from app.services.note_markers import (
    NoteMarkerConflictError,
    NoteMarkerNotFoundError,
    NoteMarkerValidationError,
    add_marker_to_entry,
    delete_marker_from_entry,
)

logger = logging.getLogger(__name__)
entry_note_markers_router = APIRouter()


@entry_note_markers_router.post(
    "/{entry_id}/note-markers",
    response_model=EntryNoteMarkerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a note marker to an entry",
)
@limiter.limit("60/minute")
async def create_note_marker_endpoint(
    request: Request,
    entry_id: uuid.UUID,
    payload: EntryNoteMarkerCreate,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> EntryNoteMarkerResponse:
    try:
        marker = await add_marker_to_entry(
            db,
            user_id=user.id,
            entry_id=entry_id,
            payload=payload,
        )
    except NoteMarkerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="entry not found"
        ) from exc
    except NoteMarkerValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except NoteMarkerConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return EntryNoteMarkerResponse.model_validate(marker)


@entry_note_markers_router.delete(
    "/{entry_id}/note-markers/{marker_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a note marker from an entry",
)
@limiter.limit("60/minute")
async def delete_note_marker_endpoint(
    request: Request,
    entry_id: uuid.UUID,
    marker_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    try:
        await delete_marker_from_entry(
            db,
            user_id=user.id,
            entry_id=entry_id,
            marker_id=marker_id,
        )
    except NoteMarkerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="marker not found"
        ) from exc
