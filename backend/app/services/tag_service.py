"""Tag service — business logic for tag CRUD and entry-tag assignment.

Layering
--------
- Endpoints validate HTTP and shape responses.
- This module owns the business rules:
    * The user can only mutate *their own* custom tags. Default tags
      are read-only (``EntryTagOperationDeniedError``).
    * Slug uniqueness conflicts are surfaced as
      :class:`TagConflictError` so the endpoint can map them to 409.
    * Assigning tags to an entry replaces the current tag set — the
      service deletes the missing rows and inserts the new ones, all
      keyed on the entry's ``user_id`` (denormalised on the link row
      so RLS works without a join).

Privacy
-------
Tag slugs and names *can* leak behavioural data when associated with an
entry. This service therefore never logs slug, name or tag IDs — only
``user_id`` and operation identifiers go to the structured log. The
log-scrubber test in ``test_tags.py`` enforces this.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.tag import EntryTag, Tag
from app.schemas.tag import TagCreate, TagUpdate

logger = logging.getLogger(__name__)

# Cap list responses for safety. Defaults will always fit (~30); custom
# tags rarely exceed 50 per user. The cap is a guard rail.
DEFAULT_TAG_LIST_LIMIT = 200
MAX_TAG_LIST_LIMIT = 1000


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TagError(Exception):
    """Base class for tag-service errors."""


class TagNotFoundError(TagError):
    """Tag does not exist or does not belong to the user."""


class TagConflictError(TagError):
    """Slug already exists for this user."""


class TagOperationDeniedError(TagError):
    """Operation is not allowed (e.g. mutating a default tag)."""


class EntryNotFoundForTagError(TagError):
    """The target entry does not exist or belongs to a different user."""


class TagsNotFoundError(TagError):
    """One or more tag IDs in the assignment payload are not visible to the user."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_owned_custom_tag(db: AsyncSession, *, tag_id: uuid.UUID, user_id: uuid.UUID) -> Tag:
    """Fetch a custom tag the user owns or raise :class:`TagNotFoundError`.

    Default tags (``user_id IS NULL``) are excluded — this helper is
    used for write paths where defaults are not editable.
    """
    result = await db.execute(
        select(Tag).where(
            Tag.id == tag_id,
            Tag.user_id == user_id,
            Tag.is_default.is_(False),
        )
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        raise TagNotFoundError("tag not found")
    return tag


async def _get_owned_entry(db: AsyncSession, *, entry_id: uuid.UUID, user_id: uuid.UUID) -> Entry:
    """Fetch an entry the user owns or raise :class:`EntryNotFoundForTagError`."""
    result = await db.execute(select(Entry).where(Entry.id == entry_id, Entry.user_id == user_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise EntryNotFoundForTagError("entry not found")
    return entry


# ---------------------------------------------------------------------------
# Public API — Tag CRUD
# ---------------------------------------------------------------------------


async def list_default_tags(db: AsyncSession) -> list[Tag]:
    """Return all curated default tags ordered by category, slug."""
    result = await db.execute(
        select(Tag).where(Tag.is_default.is_(True)).order_by(Tag.category.asc(), Tag.slug.asc())
    )
    return list(result.scalars().all())


async def list_visible_tags(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = DEFAULT_TAG_LIST_LIMIT,
) -> list[Tag]:
    """Return defaults *plus* the user's own custom tags, ordered by slug."""
    limit = max(1, min(limit, MAX_TAG_LIST_LIMIT))
    stmt = (
        select(Tag)
        .where((Tag.is_default.is_(True)) | (Tag.user_id == user_id))
        .order_by(Tag.category.asc(), Tag.slug.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_custom_tag(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: TagCreate,
) -> Tag:
    """Create a custom tag for ``user_id``.

    Raises:
        TagConflictError: the user already owns a tag with this slug,
            *or* the slug clashes with a curated default.
    """
    # Pre-check against defaults: a custom tag must not shadow a curated
    # slug, otherwise the frontend can't distinguish them by slug alone.
    default_clash = await db.execute(
        select(Tag).where(Tag.is_default.is_(True), Tag.slug == payload.slug)
    )
    if default_clash.scalar_one_or_none() is not None:
        raise TagConflictError("slug clashes with a default tag")

    tag = Tag(
        user_id=user_id,
        slug=payload.slug,
        name=payload.name,
        category=payload.category,
        icon=payload.icon,
        color=payload.color,
        is_default=False,
    )
    db.add(tag)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise TagConflictError("tag with this slug already exists") from exc

    logger.info(
        "tag.created",
        extra={"user_id": str(user_id), "tag_id": str(tag.id)},
    )
    return tag


async def update_custom_tag(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
    payload: TagUpdate,
) -> Tag:
    """Update a custom tag the user owns.

    Raises:
        TagNotFoundError: tag does not exist or belongs to someone else
            (or is a curated default — defaults are read-only and the
            ownership filter excludes them).
    """
    tag = await _get_owned_custom_tag(db, tag_id=tag_id, user_id=user_id)

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(tag, field, value)

    await db.flush()

    logger.info(
        "tag.updated",
        extra={"user_id": str(user_id), "tag_id": str(tag.id)},
    )
    return tag


async def delete_custom_tag(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> None:
    """Delete a custom tag the user owns.

    The DB cascades to ``entry_tags`` so historical entries lose the
    reference cleanly.
    """
    tag = await _get_owned_custom_tag(db, tag_id=tag_id, user_id=user_id)
    await db.delete(tag)
    await db.flush()

    logger.info(
        "tag.deleted",
        extra={"user_id": str(user_id), "tag_id": str(tag_id)},
    )


# ---------------------------------------------------------------------------
# Public API — Entry-tag assignment
# ---------------------------------------------------------------------------


async def list_tags_for_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
) -> list[Tag]:
    """Return tags currently assigned to ``entry_id`` (owner-scoped)."""
    await _get_owned_entry(db, entry_id=entry_id, user_id=user_id)

    stmt = (
        select(Tag)
        .join(EntryTag, EntryTag.tag_id == Tag.id)
        .where(EntryTag.entry_id == entry_id, EntryTag.user_id == user_id)
        .order_by(Tag.category.asc(), Tag.slug.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def assign_tags_to_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    entry_id: uuid.UUID,
    tag_ids: Sequence[uuid.UUID],
) -> list[Tag]:
    """Replace the entry's tag set with ``tag_ids``.

    The list semantically replaces the current set: tags missing from
    the new list are removed; tags new in the list are inserted. Tags
    already present are left untouched.

    Raises:
        EntryNotFoundForTagError: entry not visible to the user.
        TagsNotFoundError: at least one of ``tag_ids`` is not visible to
            the user (neither a default nor one of their custom tags).
    """
    await _get_owned_entry(db, entry_id=entry_id, user_id=user_id)

    target_ids = set(tag_ids)

    # Validate all tag IDs are visible to the user. Defaults + own customs.
    if target_ids:
        visible = await db.execute(
            select(Tag.id).where(
                Tag.id.in_(target_ids),
                (Tag.is_default.is_(True)) | (Tag.user_id == user_id),
            )
        )
        visible_ids = {row[0] for row in visible.all()}
        missing = target_ids - visible_ids
        if missing:
            raise TagsNotFoundError(f"unknown or inaccessible tag ids: {sorted(map(str, missing))}")

    # Compute current set and the diff.
    current = await db.execute(
        select(EntryTag.tag_id).where(
            EntryTag.entry_id == entry_id,
            EntryTag.user_id == user_id,
        )
    )
    current_ids = {row[0] for row in current.all()}

    to_add = target_ids - current_ids
    to_remove = current_ids - target_ids

    if to_remove:
        await db.execute(
            delete(EntryTag).where(
                EntryTag.entry_id == entry_id,
                EntryTag.user_id == user_id,
                EntryTag.tag_id.in_(to_remove),
            )
        )

    for tid in to_add:
        db.add(EntryTag(entry_id=entry_id, tag_id=tid, user_id=user_id))

    await db.flush()

    logger.info(
        "entry.tags.assigned",
        extra={
            "user_id": str(user_id),
            "entry_id": str(entry_id),
            "added_count": len(to_add),
            "removed_count": len(to_remove),
        },
    )

    # Return the new tag set (sorted, full Tag rows).
    if not target_ids:
        return []
    refreshed = await db.execute(
        select(Tag).where(Tag.id.in_(target_ids)).order_by(Tag.category.asc(), Tag.slug.asc())
    )
    return list(refreshed.scalars().all())


__all__ = [
    "DEFAULT_TAG_LIST_LIMIT",
    "EntryNotFoundForTagError",
    "MAX_TAG_LIST_LIMIT",
    "TagConflictError",
    "TagError",
    "TagNotFoundError",
    "TagOperationDeniedError",
    "TagsNotFoundError",
    "assign_tags_to_entry",
    "create_custom_tag",
    "delete_custom_tag",
    "list_default_tags",
    "list_tags_for_entry",
    "list_visible_tags",
    "update_custom_tag",
]
