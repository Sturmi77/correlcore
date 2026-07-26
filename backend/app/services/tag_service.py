"""Tag service — business logic for tag CRUD and entry-tag assignment.

Layering
--------
- Endpoints validate HTTP and shape responses.
- This module owns the business rules:
    * The user mutates own custom tags directly. Default-tag edits
      create user-owned copy-on-write overrides so curated defaults
      never change globally.
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
from collections import defaultdict
from collections.abc import Iterable, Sequence

from sqlalchemy import delete, exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

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


class TagValidationError(TagError):
    """Tag update would violate tag field consistency."""


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


async def _get_editable_tag(db: AsyncSession, *, tag_id: uuid.UUID, user_id: uuid.UUID) -> Tag:
    """Fetch an own custom tag or a curated default tag for copy-on-write."""
    result = await db.execute(
        select(Tag).where(
            Tag.id == tag_id,
            (Tag.user_id == user_id) | (Tag.is_default.is_(True)),
        )
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        raise TagNotFoundError("tag not found")
    return tag


async def _find_user_override(db: AsyncSession, *, user_id: uuid.UUID, slug: str) -> Tag | None:
    """Return the user's copy-on-write row for a default slug, if present."""
    result = await db.execute(
        select(Tag).where(
            Tag.user_id == user_id,
            Tag.slug == slug,
            Tag.is_default.is_(False),
        )
    )
    return result.scalar_one_or_none()


def canonicalize_tags_by_slug(
    tags: Iterable[Tag],
) -> tuple[dict[uuid.UUID, uuid.UUID], dict[uuid.UUID, Tag]]:
    """Collapse default/override rows that share a slug onto one canonical tag.

    Copy-on-write overrides keep the curated slug but use a distinct database
    ID. Analytics must treat both IDs as one semantic tag so heatmaps and
    co-occurrence matrices do not show duplicate rows.
    """

    tags_by_slug: dict[str, list[Tag]] = defaultdict(list)
    for tag in tags:
        tags_by_slug[tag.slug].append(tag)

    canonical_by_slug = {
        slug: sorted(
            items,
            key=lambda item: (item.is_default, item.name.casefold(), str(item.id)),
        )[0]
        for slug, items in tags_by_slug.items()
    }
    aliases = {
        tag.id: canonical_by_slug[tag.slug].id for items in tags_by_slug.values() for tag in items
    }
    return aliases, {tag.id: tag for tag in canonical_by_slug.values()}


async def remap_entry_tags_from_default_to_override(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    default_tag_id: uuid.UUID,
    override_tag_id: uuid.UUID,
) -> int:
    """Repoint historical ``entry_tags`` from a default tag to its user override.

    Safe to run repeatedly. Entries that already link the override drop the
    leftover default link; remaining default links are updated in place.
    Returns the number of link rows deleted or updated.
    """

    if default_tag_id == override_tag_id:
        return 0

    delete_result = await db.execute(
        delete(EntryTag).where(
            EntryTag.user_id == user_id,
            EntryTag.tag_id == default_tag_id,
            EntryTag.entry_id.in_(
                select(EntryTag.entry_id).where(
                    EntryTag.user_id == user_id,
                    EntryTag.tag_id == override_tag_id,
                )
            ),
        )
    )
    update_result = await db.execute(
        update(EntryTag)
        .where(
            EntryTag.user_id == user_id,
            EntryTag.tag_id == default_tag_id,
        )
        .values(tag_id=override_tag_id)
    )
    await db.flush()
    deleted = int(getattr(delete_result, "rowcount", 0) or 0)
    updated = int(getattr(update_result, "rowcount", 0) or 0)
    changed = deleted + updated
    if changed:
        logger.info(
            "tag.entry_links.remapped",
            extra={
                "user_id": str(user_id),
                "deleted_count": deleted,
                "updated_count": updated,
            },
        )
    return changed


async def remap_all_tag_alias_entry_links(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
) -> int:
    """Remap default→override ``entry_tags`` for all (or one) users with COW rows."""

    default_tag = aliased(Tag)
    override_tag = aliased(Tag)
    stmt = (
        select(override_tag.user_id, default_tag.id, override_tag.id)
        .join(
            default_tag,
            (default_tag.slug == override_tag.slug) & default_tag.is_default.is_(True),
        )
        .where(
            override_tag.is_default.is_(False),
            override_tag.user_id.is_not(None),
        )
    )
    if user_id is not None:
        stmt = stmt.where(override_tag.user_id == user_id)

    result = await db.execute(stmt)
    total = 0
    for owner_id, default_id, override_id in result.all():
        if owner_id is None:
            continue
        total += await remap_entry_tags_from_default_to_override(
            db,
            user_id=owner_id,
            default_tag_id=default_id,
            override_tag_id=override_id,
        )
    return total


def _visible_tag_predicate(user_id: uuid.UUID) -> ColumnElement[bool]:
    """Return the visibility predicate for defaults plus user overrides."""
    override = aliased(Tag)
    shadowed_default = exists(
        select(override.id).where(
            override.user_id == user_id,
            override.slug == Tag.slug,
            override.is_default.is_(False),
        )
    )
    return (Tag.user_id == user_id) | (Tag.is_default.is_(True) & ~shadowed_default)


def visible_tag_predicate(user_id: uuid.UUID) -> ColumnElement[bool]:
    """Return the public visibility predicate for defaults plus user overrides."""
    return _visible_tag_predicate(user_id)


def active_tag_predicate(user_id: uuid.UUID) -> ColumnElement[bool]:
    """Return true for tags that should participate in new user calculations.

    Default tags can be hidden through a user-owned override with the same slug.
    Historical entry links may still point at the original default row, so
    calculation queries need to treat that hidden override as shadowing too.

    Prefer :func:`analytics_tag_predicate` for insight/stats/cluster paths —
    it also respects ``include_in_analytics``.
    """
    override = aliased(Tag)
    hidden_override = exists(
        select(override.id).where(
            override.user_id == user_id,
            override.slug == Tag.slug,
            override.is_default.is_(False),
            override.is_hidden.is_(True),
        )
    )
    return Tag.is_hidden.is_(False) & ~hidden_override


def analytics_tag_predicate(user_id: uuid.UUID) -> ColumnElement[bool]:
    """Return true for tags that should appear in analytics calculations.

    Combines :func:`active_tag_predicate` with ``include_in_analytics``. A
    user-owned override with ``include_in_analytics=False`` also shadows the
    curated default slug (historical links may still point at the default).
    Habit adherence deliberately uses :func:`visible_tag_predicate` instead.
    """
    override = aliased(Tag)
    analytics_excluded_override = exists(
        select(override.id).where(
            override.user_id == user_id,
            override.slug == Tag.slug,
            override.is_default.is_(False),
            override.include_in_analytics.is_(False),
        )
    )
    return (
        active_tag_predicate(user_id)
        & Tag.include_in_analytics.is_(True)
        & ~analytics_excluded_override
    )


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
    include_hidden: bool = False,
) -> list[Tag]:
    """Return defaults plus user tags, with overrides shadowing defaults."""
    limit = max(1, min(limit, MAX_TAG_LIST_LIMIT))
    stmt = (
        select(Tag)
        .where(_visible_tag_predicate(user_id))
        .order_by(Tag.category.asc(), Tag.slug.asc())
        .limit(limit)
    )
    if not include_hidden:
        stmt = stmt.where(Tag.is_hidden.is_(False))
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
        include_in_analytics=payload.include_in_analytics,
        habit_type=payload.habit_type,
        target_frequency=payload.target_frequency,
        is_default=False,
    )
    db.add(tag)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise TagConflictError("tag with this slug already exists") from exc

    from app.services.sync_service import record_tag_revision

    await record_tag_revision(db, user_id=user_id, tag_id=tag.id, operation="upsert", tag=tag)

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
    """Update an own tag, or create/update an override for a default tag.

    Raises:
        TagNotFoundError: tag does not exist or belongs to someone else.
    """
    source = await _get_editable_tag(db, tag_id=tag_id, user_id=user_id)
    default_source: Tag | None = source if source.is_default else None
    if source.is_default:
        tag = await _find_user_override(db, user_id=user_id, slug=source.slug)
        if tag is None:
            tag = Tag(
                user_id=user_id,
                slug=source.slug,
                name=source.name,
                category=source.category,
                icon=source.icon,
                color=source.color,
                is_default=False,
                is_hidden=False,
                include_in_analytics=source.include_in_analytics,
                habit_type=source.habit_type,
                target_frequency=source.target_frequency,
            )
            db.add(tag)
    else:
        tag = source

    data = payload.model_dump(exclude_unset=True)
    next_habit_type = data.get("habit_type", tag.habit_type)
    next_target_frequency = data.get("target_frequency", tag.target_frequency)
    if next_habit_type == "none":
        data["target_frequency"] = None
    elif next_target_frequency is None:
        raise TagValidationError("target_frequency is required for habit tags")

    for field, value in data.items():
        setattr(tag, field, value)

    await db.flush()

    if default_source is None:
        default_result = await db.execute(
            select(Tag).where(Tag.is_default.is_(True), Tag.slug == tag.slug)
        )
        default_source = default_result.scalar_one_or_none()
    if default_source is not None:
        await remap_entry_tags_from_default_to_override(
            db,
            user_id=user_id,
            default_tag_id=default_source.id,
            override_tag_id=tag.id,
        )

    from app.services.sync_service import record_tag_revision

    await record_tag_revision(db, user_id=user_id, tag_id=tag.id, operation="upsert", tag=tag)

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

    from app.services.sync_service import record_tag_revision

    await record_tag_revision(db, user_id=user_id, tag_id=tag_id, operation="delete")

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
    record_revision: bool = True,
) -> list[Tag]:
    """Replace the entry's tag set with ``tag_ids``.

    The list semantically replaces the current set: tags missing from
    the new list are removed; tags new in the list are inserted. Tags
    already present are left untouched.

    Hiding a tag keeps historical ``entry_tags`` links (see FRONTEND.md /
    M3.5 tag lifecycle). Re-saving an entry that still carries those IDs
    must succeed: pickers omit hidden tags for *new* assignments, but
    ``list_tags_for_entry`` returns them so the client can round-trip the
    existing set. Rejecting already-linked hidden IDs 422'd every edit and,
    via offline sync, raised an uncaught error that aborted the whole push
    batch so newer pending changes never acked.

    When ``record_revision`` is true (REST default), emit an entry upsert
    into ``sync_revision_log`` so offline pull sees association changes.
    Sync push passes false because it appends its own revision after merge.

    Raises:
        EntryNotFoundForTagError: entry not visible to the user.
        TagsNotFoundError: at least one of ``tag_ids`` is not visible to
            the user (neither a default nor one of their custom tags) and
            is not already linked on this entry.
    """
    entry = await _get_owned_entry(db, entry_id=entry_id, user_id=user_id)

    target_ids = set(tag_ids)

    # Current links first — needed to allow already-linked hidden tags.
    current = await db.execute(
        select(EntryTag.tag_id).where(
            EntryTag.entry_id == entry_id,
            EntryTag.user_id == user_id,
        )
    )
    current_ids = {row[0] for row in current.all()}

    # New IDs must be visible and not hidden. IDs already on this entry may
    # remain even when the tag was later hidden (historical retention).
    if target_ids:
        visible = await db.execute(
            select(Tag.id).where(
                Tag.id.in_(target_ids),
                _visible_tag_predicate(user_id),
                Tag.is_hidden.is_(False),
            )
        )
        visible_ids = {row[0] for row in visible.all()}
        allowed_ids = visible_ids | (target_ids & current_ids)
        missing = target_ids - allowed_ids
        if missing:
            raise TagsNotFoundError(f"unknown or inaccessible tag ids: {sorted(map(str, missing))}")

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

    if record_revision and (to_add or to_remove):
        from app.services.sync_service import record_entry_upsert_revision

        await record_entry_upsert_revision(db, user_id=user_id, entry=entry)

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
    "TagValidationError",
    "TagsNotFoundError",
    "active_tag_predicate",
    "analytics_tag_predicate",
    "assign_tags_to_entry",
    "canonicalize_tags_by_slug",
    "create_custom_tag",
    "delete_custom_tag",
    "list_default_tags",
    "list_tags_for_entry",
    "list_visible_tags",
    "remap_all_tag_alias_entry_links",
    "remap_entry_tags_from_default_to_override",
    "update_custom_tag",
    "visible_tag_predicate",
]
