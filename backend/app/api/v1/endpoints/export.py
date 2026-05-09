"""Convenience JSON/CSV export endpoints for M2."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.db.session import get_session
from app.models.user import User
from app.services.export_service import (
    build_export_envelope,
    export_filename,
    render_export_csv,
    render_export_json,
)

router = APIRouter()


@router.get("/json", summary="Download the current user's data as JSON")
async def export_json_endpoint(
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> Response:
    envelope = await build_export_envelope(db, user=user)
    return Response(
        content=render_export_json(envelope),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{export_filename("json")}"'},
    )


@router.get("/csv", summary="Download the current user's entries as CSV")
async def export_csv_endpoint(
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> Response:
    envelope = await build_export_envelope(db, user=user)
    return Response(
        content=render_export_csv(envelope),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{export_filename("csv")}"'},
    )
