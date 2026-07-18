"""Note signal read + admin reprocess endpoints."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_insight_trigger_admin, get_current_verified_user
from app.core.crypto import reset_current_user_dek, set_current_user_dek
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.entry import Entry
from app.models.user import User
from app.schemas.note import EntryNoteSignalResponse
from app.services.entry_service import EntryNotFoundError, get_entry
from app.services.note_signal_extractor import (
    extract_and_store_signals_for_entry,
    list_signals_for_entry,
    load_user_dek,
)

logger = logging.getLogger(__name__)

entry_note_signals_router = APIRouter()
admin_note_signals_router = APIRouter()


@entry_note_signals_router.get(
    "/{entry_id:uuid}/note-signals",
    response_model=list[EntryNoteSignalResponse],
    summary="List extracted note signals for an entry",
)
@limiter.limit("120/minute")
async def list_entry_note_signals_endpoint(
    request: Request,
    entry_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> list[EntryNoteSignalResponse]:
    try:
        await get_entry(db, user_id=user.id, entry_id=entry_id)
    except EntryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="entry not found"
        ) from exc

    signals = await list_signals_for_entry(db, user_id=user.id, entry_id=entry_id)
    return [EntryNoteSignalResponse.model_validate(signal) for signal in signals]


@admin_note_signals_router.post(
    "/entries/{entry_id:uuid}/note-signals/reprocess",
    response_model=list[EntryNoteSignalResponse],
    summary="Re-run note signal extraction for one entry (admin)",
)
@limiter.limit("30/minute")
async def reprocess_entry_note_signals_endpoint(
    request: Request,
    entry_id: uuid.UUID,
    _admin: User = Depends(get_current_insight_trigger_admin),
    db: AsyncSession = Depends(get_session),
) -> list[EntryNoteSignalResponse]:
    """Operator reprocess — gated by ``INSIGHT_TRIGGER_ADMIN_EMAILS`` (same list as insight trigger)."""

    result = await db.execute(select(Entry).where(Entry.id == entry_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="entry not found")

    dek_token = None
    try:
        dek = await load_user_dek(db, user_id=entry.user_id)
        if dek is not None:
            dek_token = set_current_user_dek(entry.user_id, dek)
        signals = await extract_and_store_signals_for_entry(
            db,
            user_id=entry.user_id,
            entry_id=entry_id,
        )
    finally:
        if dek_token is not None:
            reset_current_user_dek(dek_token)

    return [EntryNoteSignalResponse.model_validate(signal) for signal in signals]
