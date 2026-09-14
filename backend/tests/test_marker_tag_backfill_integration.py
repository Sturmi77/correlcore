"""Integration tests for the marker → tag backfill service (#895).

These exercise the real service-layer paths against PostgreSQL: predefined 1:1
links, per-user custom-tag creation, hidden-note exclusion, copy-on-write
override preference, the per-entry assignment cap, idempotency, and the
``sync_revision_log`` rows offline clients depend on — the DB-fixture coverage
the raw-SQL draft (#899) could not provide.

Opt-in locally: set ``CORRELCORE_RUN_INTEGRATION=1`` after migrations and service
containers are up. CI runs this in the ``migrations-smoke`` / integration job,
where ``alembic upgrade head`` has seeded the curated default tags (043/047).
"""

from __future__ import annotations

import os
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, bind_rls_current_user
from app.models.entry import Entry, EntrySlot, EntrySource, NoteVisibility, WorkContext
from app.models.entry_note import EntryNoteMarker
from app.models.tag import EntryTag, Tag, TagCategory
from app.schemas.tag import MAX_TAGS_PER_ENTRY
from app.services.marker_tag_backfill_service import (
    _list_backfill_user_ids,
    backfill_marker_tags,
)
from app.services.tag_service import TagConflictError

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE_DATE = date(2026, 1, 1)


def _integration_enabled() -> bool:
    return os.getenv("CORRELCORE_RUN_INTEGRATION") == "1"


async def _create_user(session: AsyncSession, *, active: bool = True) -> uuid.UUID:
    uid = uuid.uuid4()
    await bind_rls_current_user(session, uid)
    await session.execute(
        text(
            "INSERT INTO users (id, email, hashed_password, is_active, is_verified) "
            "VALUES (:id, :email, 'x', :active, true)"
        ),
        {"id": uid, "email": f"marker-895-{uid.hex[:8]}@localhost.dev", "active": active},
    )
    # AsyncSessionLocal() does not auto-commit (only the get_session dependency
    # does), so persist the user before later sessions reference it via FK.
    await session.commit()
    return uid


def _make_entry(uid: uuid.UUID, day_offset: int, *, hidden: bool = False) -> Entry:
    entry = Entry()
    entry.id = uuid.uuid4()
    entry.user_id = uid
    entry.entry_date = _BASE_DATE + timedelta(days=day_offset)
    entry.slot = EntrySlot.DAY
    entry.mood_score = 3
    entry.energy = 3
    entry.stress = 3
    entry.source = EntrySource.DIRECT
    entry.work_context = WorkContext.OFFICE
    entry.note_visibility = NoteVisibility.HIDDEN if hidden else NoteVisibility.FULL
    return entry


def _make_marker(uid: uuid.UUID, entry_id: uuid.UUID, marker: str) -> EntryNoteMarker:
    row = EntryNoteMarker()
    row.id = uuid.uuid4()
    row.entry_id = entry_id
    row.user_id = uid
    row.marker = marker
    return row


async def _entry_tag_ids(session: AsyncSession, entry_id: uuid.UUID) -> set[uuid.UUID]:
    result = await session.execute(select(EntryTag.tag_id).where(EntryTag.entry_id == entry_id))
    return {row[0] for row in result.all()}


async def _default_tag_id(session: AsyncSession, slug: str) -> uuid.UUID:
    result = await session.execute(select(Tag.id).where(Tag.is_default.is_(True), Tag.slug == slug))
    return result.scalar_one()


async def _cleanup_user(uid: uuid.UUID) -> None:
    async with AsyncSessionLocal() as session:
        await bind_rls_current_user(session, uid)
        # FK cascades from users → entries/tags/markers/entry_tags/sync_* rows.
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        await session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backfill_predefined_custom_hidden_and_idempotent() -> None:
    if not _integration_enabled():
        pytest.skip("requires real PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    async with AsyncSessionLocal() as session:
        uid = await _create_user(session)

    try:
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            e_full = _make_entry(uid, 0)
            e_hidden = _make_entry(uid, 1, hidden=True)
            e_ach = _make_entry(uid, 2)
            session.add_all([e_full, e_hidden, e_ach])
            session.add_all(
                [
                    _make_marker(uid, e_full.id, "conflict"),
                    _make_marker(uid, e_full.id, "proben"),  # custom
                    _make_marker(uid, e_hidden.id, "travel"),  # excluded (hidden note)
                    _make_marker(uid, e_ach.id, "work"),  # generic → skipped
                    _make_marker(uid, e_ach.id, "achievement"),
                ]
            )
            await session.commit()
            full_id, hidden_id, ach_id = e_full.id, e_hidden.id, e_ach.id

        async with AsyncSessionLocal() as session:
            summary = await backfill_marker_tags(session, user_id=uid)
            await session.commit()

        assert summary.entries_updated == 2
        assert summary.predefined_links_added == 2  # conflict + achievement
        assert summary.custom_tags_created == 1  # proben
        assert summary.custom_links_added == 1

        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            conflict_id = await _default_tag_id(session, "conflict")
            achievement_id = await _default_tag_id(session, "achievement")

            custom = (
                await session.execute(
                    select(Tag).where(
                        Tag.user_id == uid,
                        Tag.slug == "proben",
                        Tag.is_default.is_(False),
                    )
                )
            ).scalar_one()
            assert custom.category == TagCategory.OTHER
            assert custom.name == "proben"

            assert await _entry_tag_ids(session, full_id) == {conflict_id, custom.id}
            assert await _entry_tag_ids(session, hidden_id) == set()  # hidden note excluded
            assert await _entry_tag_ids(session, ach_id) == {achievement_id}

            # Sync revisions were emitted so offline clients pull the new links.
            entry_revs = (
                await session.execute(
                    text(
                        "SELECT count(*) FROM sync_revision_log "
                        "WHERE user_id = :id AND entity_type = 'entry' AND operation = 'upsert'"
                    ),
                    {"id": uid},
                )
            ).scalar_one()
            assert entry_revs >= 2
            tag_revs = (
                await session.execute(
                    text(
                        "SELECT count(*) FROM sync_revision_log "
                        "WHERE user_id = :id AND entity_type = 'tag' AND operation = 'upsert'"
                    ),
                    {"id": uid},
                )
            ).scalar_one()
            assert tag_revs >= 1  # the created custom tag

        # Second run is a no-op (idempotent).
        async with AsyncSessionLocal() as session:
            again = await backfill_marker_tags(session, user_id=uid)
            await session.commit()
        assert again.entries_updated == 0
        assert again.custom_tags_created == 0
        assert again.predefined_links_added == 0
        assert again.custom_links_added == 0
    finally:
        await _cleanup_user(uid)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backfill_prefers_user_override_over_default() -> None:
    if not _integration_enabled():
        pytest.skip("requires real PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    async with AsyncSessionLocal() as session:
        uid = await _create_user(session)

    try:
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            override = Tag()
            override.id = uuid.uuid4()
            override.user_id = uid
            override.slug = "conflict"  # copy-on-write override of the curated default
            override.name = "Streit"
            override.category = TagCategory.SOCIAL
            override.is_default = False
            session.add(override)

            entry = _make_entry(uid, 0)
            session.add(entry)
            session.add(_make_marker(uid, entry.id, "conflict"))
            await session.commit()
            entry_id, override_id = entry.id, override.id

        async with AsyncSessionLocal() as session:
            await backfill_marker_tags(session, user_id=uid)
            await session.commit()

        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            default_id = await _default_tag_id(session, "conflict")
            linked = await _entry_tag_ids(session, entry_id)
            assert linked == {override_id}  # override wins
            assert default_id not in linked  # never links the shadowed default
    finally:
        await _cleanup_user(uid)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backfill_preserves_assignment_cap() -> None:
    if not _integration_enabled():
        pytest.skip("requires real PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    async with AsyncSessionLocal() as session:
        uid = await _create_user(session)

    try:
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            entry = _make_entry(uid, 0)
            session.add(entry)
            # Fill the entry to exactly the cap with custom tags. Flush the tags
            # (and entry) before the link rows so the entry_tags FK is satisfied.
            tags = []
            for i in range(MAX_TAGS_PER_ENTRY):
                tag = Tag()
                tag.id = uuid.uuid4()
                tag.user_id = uid
                tag.slug = f"cap-{i:02d}"
                tag.name = f"Cap {i}"
                tag.category = TagCategory.OTHER
                tag.is_default = False
                session.add(tag)
                tags.append(tag)
            await session.flush()
            for tag in tags:
                link = EntryTag()
                link.entry_id = entry.id
                link.tag_id = tag.id
                link.user_id = uid
                session.add(link)
            session.add(_make_marker(uid, entry.id, "conflict"))
            await session.commit()
            entry_id = entry.id

        async with AsyncSessionLocal() as session:
            summary = await backfill_marker_tags(session, user_id=uid)
            await session.commit()

        assert summary.skipped_over_cap >= 1
        assert summary.entries_updated == 0  # nothing added → no revision churn

        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            conflict_id = await _default_tag_id(session, "conflict")
            linked = await _entry_tag_ids(session, entry_id)
            assert len(linked) == MAX_TAGS_PER_ENTRY  # cap not exceeded
            assert conflict_id not in linked  # marker dropped rather than overflowing
    finally:
        await _cleanup_user(uid)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backfill_does_not_create_orphan_tag_on_full_entry() -> None:
    # A custom marker seen only on an already-full entry must not create a tag
    # (it would sit unlinked in the user's catalogue). #900 review.
    if not _integration_enabled():
        pytest.skip("requires real PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    async with AsyncSessionLocal() as session:
        uid = await _create_user(session)

    try:
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            entry = _make_entry(uid, 0)
            session.add(entry)
            tags = []
            for i in range(MAX_TAGS_PER_ENTRY):
                tag = Tag()
                tag.id = uuid.uuid4()
                tag.user_id = uid
                tag.slug = f"cap-{i:02d}"
                tag.name = f"Cap {i}"
                tag.category = TagCategory.OTHER
                tag.is_default = False
                session.add(tag)
                tags.append(tag)
            await session.flush()
            for tag in tags:
                link = EntryTag()
                link.entry_id = entry.id
                link.tag_id = tag.id
                link.user_id = uid
                session.add(link)
            # A brand-new custom marker that has no existing tag.
            session.add(_make_marker(uid, entry.id, "brandneu"))
            await session.commit()

        async with AsyncSessionLocal() as session:
            summary = await backfill_marker_tags(session, user_id=uid)
            await session.commit()

        assert summary.custom_tags_created == 0  # no orphan tag created
        assert summary.skipped_over_cap >= 1

        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            orphan = (
                await session.execute(
                    select(Tag.id).where(Tag.user_id == uid, Tag.slug == "brandneu")
                )
            ).scalar_one_or_none()
            assert orphan is None  # nothing left in the user's catalogue
    finally:
        await _cleanup_user(uid)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backfill_includes_disabled_users_and_commits_per_user() -> None:
    # Enumeration must cover reversibly disabled accounts, and the real run's
    # per-user commit path must persist a converted user. #900 review.
    if not _integration_enabled():
        pytest.skip("requires real PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    async with AsyncSessionLocal() as session:
        uid = await _create_user(session, active=False)

    try:
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            entry = _make_entry(uid, 0)
            session.add(entry)
            session.add(_make_marker(uid, entry.id, "conflict"))
            await session.commit()
            entry_id = entry.id

        # Enumeration (user_id=None) includes the disabled account.
        async with AsyncSessionLocal() as session:
            all_ids = await _list_backfill_user_ids(session, user_id=None)
            assert uid in all_ids

        # commit_per_user=True commits the user; a later session sees the link.
        async with AsyncSessionLocal() as session:
            summary = await backfill_marker_tags(session, user_id=uid, commit_per_user=True)
        assert summary.users_processed == 1
        assert summary.predefined_links_added == 1

        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            conflict_id = await _default_tag_id(session, "conflict")
            assert await _entry_tag_ids(session, entry_id) == {conflict_id}
    finally:
        await _cleanup_user(uid)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backfill_isolates_a_failing_user(monkeypatch: pytest.MonkeyPatch) -> None:
    # A user whose custom-tag creation raises (e.g. a concurrent slug insert
    # rolling the session back) is rolled back and counted, not silently
    # committed with lying counters; other users are unaffected. #900 review.
    if not _integration_enabled():
        pytest.skip("requires real PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    async with AsyncSessionLocal() as session:
        ok_uid = await _create_user(session)
        bad_uid = await _create_user(session)

    try:
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, ok_uid)
            ok_entry = _make_entry(ok_uid, 0)
            session.add(ok_entry)
            session.add(_make_marker(ok_uid, ok_entry.id, "conflict"))  # predefined, no create
            await session.commit()
            ok_entry_id = ok_entry.id
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, bad_uid)
            bad_entry = _make_entry(bad_uid, 0)
            session.add(bad_entry)
            session.add(_make_marker(bad_uid, bad_entry.id, "proben"))  # custom, needs create
            await session.commit()
            bad_entry_id = bad_entry.id

        async def _boom(db, *, user_id, payload):  # type: ignore[no-untyped-def]
            raise TagConflictError("simulated concurrent slug insert")

        monkeypatch.setattr("app.services.marker_tag_backfill_service.create_custom_tag", _boom)

        # Good user (predefined only) commits; failing user is rolled back.
        async with AsyncSessionLocal() as session:
            ok_summary = await backfill_marker_tags(session, user_id=ok_uid, commit_per_user=True)
        async with AsyncSessionLocal() as session:
            bad_summary = await backfill_marker_tags(session, user_id=bad_uid, commit_per_user=True)

        assert ok_summary.users_processed == 1
        assert ok_summary.users_failed == 0
        assert bad_summary.users_failed == 1
        assert bad_summary.users_processed == 0

        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, ok_uid)
            conflict_id = await _default_tag_id(session, "conflict")
            assert await _entry_tag_ids(session, ok_entry_id) == {conflict_id}
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, bad_uid)
            assert await _entry_tag_ids(session, bad_entry_id) == set()  # rolled back
            orphan = (
                await session.execute(
                    select(Tag.id).where(Tag.user_id == bad_uid, Tag.slug == "proben")
                )
            ).scalar_one_or_none()
            assert orphan is None
    finally:
        await _cleanup_user(ok_uid)
        await _cleanup_user(bad_uid)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backfill_disambiguates_colliding_marker_slugs() -> None:
    # Distinct markers that normalise to the same base slug get distinct,
    # deterministic slugs instead of being merged onto one tag. #899 review.
    if not _integration_enabled():
        pytest.skip("requires real PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    async with AsyncSessionLocal() as session:
        uid = await _create_user(session)

    try:
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            entry = _make_entry(uid, 0)
            session.add(entry)
            # Both normalise to base slug "dog-sitting"; "dog sitting" (space)
            # sorts before "dog-sitting" (hyphen), so it keeps the base slug.
            session.add(_make_marker(uid, entry.id, "dog sitting"))
            session.add(_make_marker(uid, entry.id, "dog-sitting"))
            await session.commit()
            entry_id = entry.id

        async with AsyncSessionLocal() as session:
            summary = await backfill_marker_tags(session, user_id=uid)
            await session.commit()

        assert summary.custom_tags_created == 2  # not merged
        assert summary.custom_links_added == 2

        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            tags = (
                await session.execute(
                    select(Tag.slug, Tag.name).where(Tag.user_id == uid, Tag.is_default.is_(False))
                )
            ).all()
            by_slug = dict(tags)
            assert set(by_slug) == {"dog-sitting", "dog-sitting-2"}
            assert by_slug["dog-sitting"] == "dog sitting"  # base slug: first in sort order
            assert by_slug["dog-sitting-2"] == "dog-sitting"
            assert len(await _entry_tag_ids(session, entry_id)) == 2

        # Idempotent: a re-run adds nothing and creates no further tags.
        async with AsyncSessionLocal() as session:
            again = await backfill_marker_tags(session, user_id=uid)
            await session.commit()
        assert again.custom_tags_created == 0
        assert again.custom_links_added == 0
        assert again.entries_updated == 0
    finally:
        await _cleanup_user(uid)
