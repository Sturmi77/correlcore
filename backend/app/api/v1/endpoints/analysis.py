"""Analysis endpoints for note markers (Notes in Analysis M3)."""

from __future__ import annotations

import logging
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.note import MarkerSummaryResponse
from app.services.note_markers import NoteMarkerValidationError, aggregate_marker_summary

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/notes/marker-summary",
    response_model=MarkerSummaryResponse,
    summary="Aggregate mood averages per note marker",
)
@limiter.limit("120/minute")
async def marker_summary_endpoint(
    request: Request,
    from_date: date_type = Query(..., alias="from"),
    to_date: date_type = Query(..., alias="to"),
    markers: list[str] | None = Query(default=None),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> MarkerSummaryResponse:
    try:
        items = await aggregate_marker_summary(
            db,
            user_id=user.id,
            from_date=from_date,
            to_date=to_date,
            markers=markers,
        )
    except NoteMarkerValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return MarkerSummaryResponse(items=items, **{"from": from_date, "to": to_date})
