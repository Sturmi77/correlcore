"""049 must leave tags, entry_tags, note-signals, and non-marker insights intact.

Re-runs the production DELETE and an alembic 048↔049 round-trip against
PostgreSQL so a reviewer can reconfirm the tag blast radius. Opt-in:
``CORRELCORE_RUN_INTEGRATION=1`` after ``alembic upgrade head``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, bind_rls_current_user
from app.models.entry import Entry, EntrySlot, EntrySource, WorkContext
from app.models.entry_note import EntryNoteSignal
from app.models.insight import Insight, InsightTier, InsightType
from app.models.tag import EntryTag, Tag, TagCategory

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BACKEND = Path(__file__).resolve().parents[1]
_UNRELATED_DEFAULT_SLUGS = (
    "running",
    "family",
    "good_sleep",
    "work_intense",
    "conflict",  # converted 1:1 historically — the *row* must still be untouched
)


def _integration_enabled() -> bool:
    return os.getenv("CORRELCORE_RUN_INTEGRATION") == "1"


def _run_alembic(*args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "migrations/alembic.ini", *args],
        cwd=_BACKEND,
        check=True,
        env=os.environ.copy(),
    )


async def _fingerprint_tags(session: AsyncSession) -> list[tuple[object, ...]]:
    rows = (
        await session.execute(
            text(
                "SELECT id, user_id, slug, name, category::text, is_default, "
                "is_hidden, is_pinned, include_in_analytics "
                "FROM tags ORDER BY id"
            )
        )
    ).all()
    return [tuple(row) for row in rows]


async def _fingerprint_entry_tags(session: AsyncSession) -> list[tuple[object, ...]]:
    rows = (
        await session.execute(
            text("SELECT entry_id, tag_id, user_id FROM entry_tags ORDER BY entry_id, tag_id")
        )
    ).all()
    return [tuple(row) for row in rows]


async def _create_user(session: AsyncSession) -> uuid.UUID:
    uid = uuid.uuid4()
    await bind_rls_current_user(session, uid)
    await session.execute(
        text(
            "INSERT INTO users (id, email, hashed_password, is_active, is_verified) "
            "VALUES (:id, :email, 'x', true, true)"
        ),
        {"id": uid, "email": f"049-tags-{uid.hex[:8]}@localhost.dev"},
    )
    await session.commit()
    return uid


async def _cleanup_user(uid: uuid.UUID) -> None:
    async with AsyncSessionLocal() as session:
        await bind_rls_current_user(session, uid)
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
        await session.commit()


async def _default_tag_id(session: AsyncSession, slug: str) -> uuid.UUID:
    result = await session.execute(select(Tag.id).where(Tag.is_default.is_(True), Tag.slug == slug))
    return result.scalar_one()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_049_delete_and_drop_leave_unrelated_tags_untouched() -> None:
    if not _integration_enabled():
        pytest.skip("requires real PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    async with AsyncSessionLocal() as session:
        uid = await _create_user(session)

    marker_insight_id = uuid.uuid4()
    spearman_id = uuid.uuid4()
    tag_cooccur_id = uuid.uuid4()
    signal_id = uuid.uuid4()
    custom_tag_id = uuid.uuid4()
    entry_id = uuid.uuid4()

    try:
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            tags_before = await _fingerprint_tags(session)

            entry = Entry()
            entry.id = entry_id
            entry.user_id = uid
            entry.entry_date = date(2026, 9, 1)
            entry.slot = EntrySlot.DAY
            entry.mood_score = 3
            entry.energy = 3
            entry.stress = 3
            entry.source = EntrySource.DIRECT
            entry.work_context = WorkContext.OFFICE
            entry.created_at = datetime.now(UTC)
            entry.updated_at = datetime.now(UTC)
            session.add(entry)

            custom = Tag()
            custom.id = custom_tag_id
            custom.user_id = uid
            custom.slug = "privat-hobby"
            custom.name = "Privat Hobby"
            custom.category = TagCategory.OTHER
            custom.is_default = False
            session.add(custom)
            await session.flush()

            for slug in _UNRELATED_DEFAULT_SLUGS:
                session.add(
                    EntryTag(
                        entry_id=entry_id,
                        tag_id=await _default_tag_id(session, slug),
                        user_id=uid,
                    )
                )
            session.add(EntryTag(entry_id=entry_id, tag_id=custom_tag_id, user_id=uid))

            session.add(
                EntryNoteSignal(
                    id=signal_id,
                    entry_id=entry_id,
                    user_id=uid,
                    signal="stress_mention",
                    confidence=0.8,
                    extractor_v="test",
                )
            )
            session.add(
                Insight(
                    id=spearman_id,
                    user_id=uid,
                    insight_type=InsightType.SPEARMAN,
                    tier=InsightTier.EARLY,
                    metric="mood_score",
                    sample_n=12,
                    flags={},
                    payload={"keep": True},
                    generated_for_date=date(2026, 9, 1),
                    generated_at=datetime.now(UTC),
                )
            )
            session.add(
                Insight(
                    id=tag_cooccur_id,
                    user_id=uid,
                    insight_type=InsightType.SYMPTOM_TAG_COOCCURRENCE,
                    tier=InsightTier.EARLY,
                    metric="mood_score",
                    subject_type="tag",
                    subject_id=custom_tag_id,
                    sample_n=8,
                    flags={},
                    payload={"keep": True},
                    generated_for_date=date(2026, 9, 1),
                    generated_at=datetime.now(UTC),
                )
            )
            await session.execute(
                text(
                    "INSERT INTO insights ("
                    "id, user_id, insight_type, tier, metric, sample_n, "
                    "generated_for_date, flags, payload"
                    ") VALUES ("
                    ":id, :uid, 'note_marker_mood', 'early', 'mood_score', 8, "
                    "DATE '2026-09-01', '{}'::jsonb, '{}'::jsonb"
                    ")"
                ),
                {"id": marker_insight_id, "uid": uid},
            )
            await session.commit()

        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            tags_seeded = await _fingerprint_tags(session)
            links_seeded = await _fingerprint_entry_tags(session)
            # The production DELETE from 049 — the only DML that could hit
            # other tables if the WHERE clause were too broad.
            await session.execute(
                text("DELETE FROM insights WHERE insight_type = 'note_marker_mood'")
            )
            await session.commit()

        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            assert await _fingerprint_tags(session) == tags_seeded
            assert await _fingerprint_entry_tags(session) == links_seeded
            remaining = (
                (await session.execute(select(Insight.id).where(Insight.user_id == uid)))
                .scalars()
                .all()
            )
            assert set(remaining) == {spearman_id, tag_cooccur_id}
            signal = (
                await session.execute(
                    select(EntryNoteSignal).where(EntryNoteSignal.id == signal_id)
                )
            ).scalar_one()
            assert signal.entry_id == entry_id

        # DROP TABLE cannot cascade into tags (FKs point the other way). Prove
        # it with a real 048 → 049 round-trip on this database.
        _run_alembic("downgrade", "048")
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            await session.execute(
                text(
                    "INSERT INTO entry_note_markers (id, entry_id, user_id, marker, source) "
                    "VALUES (:id, :entry_id, :uid, 'conflict', 'user')"
                ),
                {"id": uuid.uuid4(), "entry_id": entry_id, "uid": uid},
            )
            await session.commit()
            tags_pre_drop = await _fingerprint_tags(session)
            links_pre_drop = await _fingerprint_entry_tags(session)
        try:
            _run_alembic("upgrade", "049")
            async with AsyncSessionLocal() as session:
                await bind_rls_current_user(session, uid)
                assert await _fingerprint_tags(session) == tags_pre_drop
                assert await _fingerprint_entry_tags(session) == links_pre_drop
                gone = (
                    await session.execute(
                        text(
                            "SELECT 1 FROM information_schema.tables "
                            "WHERE table_name = 'entry_note_markers'"
                        )
                    )
                ).scalar_one_or_none()
                assert gone is None
                # Catalogue rows that overlap keys must never have been rewritten.
                for slug in ("running", "family", "good_sleep", "work_intense", "conflict"):
                    row = (
                        await session.execute(
                            select(Tag.slug, Tag.is_default).where(
                                Tag.is_default.is_(True), Tag.slug == slug
                            )
                        )
                    ).one()
                    assert row[0] == slug
        finally:
            _run_alembic("upgrade", "head")

        # Global catalogue plus this user's custom tag survived the whole path.
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, uid)
            tags_after = await _fingerprint_tags(session)
            assert tags_before  # curated defaults existed before the fixture
            # Seeded rows (custom tag) remain; nothing else was rewritten.
            before_ids = {row[0] for row in tags_before}
            after_ids = {row[0] for row in tags_after}
            assert before_ids <= after_ids
            assert custom_tag_id in after_ids
            custom = (
                await session.execute(select(Tag).where(Tag.id == custom_tag_id))
            ).scalar_one()
            assert custom.slug == "privat-hobby"
            assert custom.category == TagCategory.OTHER
    finally:
        await _cleanup_user(uid)
