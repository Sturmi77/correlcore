"""Tag and entry-tag-assignment endpoints (M1, Issue #8).

Mounted under two prefixes:

- ``/api/v1/tags`` — tag CRUD (defaults + custom).
- The entry-tag assignment endpoints live alongside entries to keep the
  REST hierarchy intuitive: ``/api/v1/entries/{entry_id}/tags``.

All endpoints require an active *and verified* user. Rate-limits match
the entry-endpoint policy (60/min for write, 120/min for read).
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_verified_user
from app.core.rate_limit import limiter
from app.db.session import get_session
from app.models.user import User
from app.schemas.tag import (
    EntryTagAssignment,
    TagCreate,
    TagResponse,
    TagUpdate,
)
from app.services.tag_service import (
    DEFAULT_TAG_LIST_LIMIT,
    MAX_TAG_LIST_LIMIT,
    EntryNotFoundForTagError,
    TagConflictError,
    TagNotFoundError,
    TagsNotFoundError,
    assign_tags_to_entry,
    create_custom_tag,
    delete_custom_tag,
    list_default_tags,
    list_tags_for_entry,
    list_visible_tags,
    update_custom_tag,
)

logger = logging.getLogger(__name__)

# Two routers — one for ``/tags``, one mounted at ``/entries`` to expose
# the per-entry assignment endpoints. The router.py wires them.
tags_router = APIRouter()
entry_tags_router = APIRouter()


# ---------------------------------------------------------------------------
# /tags
# ---------------------------------------------------------------------------


@tags_router.get(
    "/default",
    response_model=list[TagResponse],
    summary="List curated default tags (no auth required)",
)
@limiter.limit("120/minute")
async def list_default_tags_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> list[TagResponse]:
    """Return the curated default tags.

    Default tags are not user-specific and the list is small (~30), so
    we expose this without an auth requirement to keep the registration
    UX snappy (the picker can render before login completes). The data
    is non-personal.
    """
    tags = await list_default_tags(db)
    return [TagResponse.model_validate(t) for t in tags]


@tags_router.get(
    "",
    response_model=list[TagResponse],
    summary="List all tags visible to the user (defaults + own customs)",
)
@limiter.limit("120/minute")
async def list_tags_endpoint(
    request: Request,
    limit: int = Query(default=DEFAULT_TAG_LIST_LIMIT, ge=1, le=MAX_TAG_LIST_LIMIT),
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> list[TagResponse]:
    tags = await list_visible_tags(db, user_id=user.id, limit=limit)
    return [TagResponse.model_validate(t) for t in tags]


@tags_router.post(
    "",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom tag",
)
@limiter.limit("60/minute")
async def create_tag_endpoint(
    request: Request,
    payload: TagCreate,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> TagResponse:
    try:
        tag = await create_custom_tag(db, user_id=user.id, payload=payload)
    except TagConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return TagResponse.model_validate(tag)


@tags_router.patch(
    "/{tag_id}",
    response_model=TagResponse,
    summary="Update a custom tag (defaults are read-only)",
)
@limiter.limit("60/minute")
async def update_tag_endpoint(
    request: Request,
    tag_id: uuid.UUID,
    payload: TagUpdate,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> TagResponse:
    try:
        tag = await update_custom_tag(db, user_id=user.id, tag_id=tag_id, payload=payload)
    except TagNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="tag not found",
        ) from exc
    return TagResponse.model_validate(tag)


@tags_router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a custom tag (defaults are read-only)",
)
@limiter.limit("60/minute")
async def delete_tag_endpoint(
    request: Request,
    tag_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    try:
        await delete_custom_tag(db, user_id=user.id, tag_id=tag_id)
    except TagNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="tag not found",
        ) from exc


# ---------------------------------------------------------------------------
# /entries/{entry_id}/tags
# ---------------------------------------------------------------------------


@entry_tags_router.get(
    "/{entry_id}/tags",
    response_model=list[TagResponse],
    summary="List tags assigned to an entry",
)
@limiter.limit("120/minute")
async def list_entry_tags_endpoint(
    request: Request,
    entry_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> list[TagResponse]:
    try:
        tags = await list_tags_for_entry(db, user_id=user.id, entry_id=entry_id)
    except EntryNotFoundForTagError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="entry not found",
        ) from exc
    return [TagResponse.model_validate(t) for t in tags]


@entry_tags_router.put(
    "/{entry_id}/tags",
    response_model=list[TagResponse],
    summary="Replace the tag set for an entry",
)
@limiter.limit("60/minute")
async def assign_entry_tags_endpoint(
    request: Request,
    entry_id: uuid.UUID,
    payload: EntryTagAssignment,
    user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_session),
) -> list[TagResponse]:
    try:
        tags = await assign_tags_to_entry(
            db,
            user_id=user.id,
            entry_id=entry_id,
            tag_ids=payload.tag_ids,
        )
    except EntryNotFoundForTagError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="entry not found",
        ) from exc
    except TagsNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return [TagResponse.model_validate(t) for t in tags]
