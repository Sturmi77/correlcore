"""Release upgrade from the schema that still owns note markers.

Each case uses a disposable PostgreSQL database. This avoids downgrading a
shared integration database and makes the old-schema fixture unavoidable.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest

pytestmark = pytest.mark.integration
_BACKEND = Path(__file__).resolve().parents[1]


def _url(database: str) -> str:
    configured = os.environ["DATABASE_URL"]
    parts = urlsplit(configured.replace("postgresql+asyncpg", "postgresql"))
    return urlunsplit((parts.scheme, parts.netloc, f"/{database}", parts.query, parts.fragment))


async def _create_database(name: str) -> None:
    admin = await asyncpg.connect(_url("postgres"))
    try:
        if not await admin.fetchval("SELECT 1 FROM pg_roles WHERE rolname = 'correlcore_app'"):
            await admin.execute("CREATE ROLE correlcore_app NOLOGIN")
        await admin.execute(f'CREATE DATABASE "{name}"')
    finally:
        await admin.close()


async def _drop_database(name: str) -> None:
    admin = await asyncpg.connect(_url("postgres"))
    try:
        await admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            name,
        )
        await admin.execute(f'DROP DATABASE IF EXISTS "{name}"')
    finally:
        await admin.close()


def _alembic(database: str, revision: str, *, succeeds: bool = True) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = _url(database).replace("postgresql://", "postgresql+asyncpg://")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "migrations/alembic.ini", "upgrade", revision],
        cwd=_BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=180 if revision in {"046", "047", "048"} else 45,
        check=False,
    )
    if succeeds and result.returncode != 0:
        pytest.fail(f"alembic upgrade {revision} failed:\n{result.stdout}\n{result.stderr}")
    if not succeeds and result.returncode == 0:
        pytest.fail("fault injection did not abort the migration")


async def _seed(database: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    user_a, user_b, visible, hidden = (uuid.uuid4() for _ in range(4))
    other = uuid.uuid4()
    full = uuid.uuid4()
    conn = await asyncpg.connect(_url(database))
    try:
        for user in (user_a, user_b):
            await conn.execute(
                "INSERT INTO users (id, email, hashed_password, is_active, is_verified) "
                "VALUES ($1, $2, 'x', true, true)",
                user,
                f"a01-{user.hex}@example.test",
            )
        for entry_id, user_id, visibility in (
            (visible, user_a, "full"),
            (hidden, user_a, "hidden"),
            (other, user_b, "full"),
            (full, user_a, "full"),
        ):
            await conn.execute(
                "INSERT INTO entries (id, user_id, entry_date, slot, mood_score, energy, stress, "
                "work_context, note_visibility) VALUES "
                "($1, $2, $4, 'day', 3, 3, 3, 'office', $3)",
                entry_id,
                user_id,
                visibility,
                date(2026, 9, 2 if entry_id == full else 3 if entry_id == hidden else 1),
            )
        await conn.execute(
            "INSERT INTO tags (id, user_id, slug, name, category, is_default) "
            "VALUES ($1, $2, 'my-custom', 'Existing', 'other', false)",
            uuid.uuid4(),
            user_a,
        )
        await conn.execute(
            "INSERT INTO tags (id, user_id, slug, name, category, is_default, is_hidden) "
            "VALUES ($1, $2, 'travel', 'Hidden override', 'other', false, true)",
            uuid.uuid4(),
            user_a,
        )
        for number in range(50):
            tag_id = uuid.uuid4()
            await conn.execute(
                "INSERT INTO tags (id, user_id, slug, name, category, is_default) "
                "VALUES ($1, $2, $3, $3, 'other', false)",
                tag_id,
                user_a,
                f"cap-{number:02d}",
            )
            await conn.execute(
                "INSERT INTO entry_tags (entry_id, tag_id, user_id) VALUES ($1, $2, $3)",
                full,
                tag_id,
                user_a,
            )
        for entry_id, user_id, marker in (
            (visible, user_a, "conflict"),
            (visible, user_a, "my custom"),
            (visible, user_a, "co llision"),
            (visible, user_a, "co-llision"),
            (visible, user_a, "work"),
            (visible, user_a, "travel"),
            (hidden, user_a, "private context"),
            (other, user_b, "my custom"),
            (full, user_a, "full cap"),
        ):
            await conn.execute(
                "INSERT INTO entry_note_markers (id, entry_id, user_id, marker, source) "
                "VALUES ($1, $2, $3, $4, 'user')",
                uuid.uuid4(),
                entry_id,
                user_id,
                marker,
            )
    finally:
        await conn.close()
    return user_a, user_b, visible, hidden


async def _verify(database: str, ids: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]) -> None:
    user_a, user_b, visible, hidden = ids
    conn = await asyncpg.connect(_url(database))
    try:
        assert await conn.fetchval("SELECT to_regclass('public.entry_note_markers')") is None
        rows = await conn.fetch(
            "SELECT t.slug, t.user_id FROM entry_tags et JOIN tags t ON t.id = et.tag_id "
            "WHERE et.entry_id = $1 ORDER BY t.slug",
            visible,
        )
        slugs = [row["slug"] for row in rows]
        assert "conflict" in slugs
        assert "my-custom" in slugs
        assert "co-llision" in slugs and "co-llision-2" in slugs
        assert "work" not in slugs
        assert "travel" not in slugs
        assert (
            await conn.fetchval("SELECT count(*) FROM entry_tags WHERE entry_id = $1", hidden) == 0
        )
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM entry_tags et JOIN entries e ON e.id = et.entry_id "
                "WHERE e.user_id = $1 AND e.entry_date = DATE '2026-09-02'",
                user_a,
            )
            == 50
        )
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM tags WHERE slug = 'full-cap' AND user_id = $1", user_a
            )
            == 0
        )
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM tags WHERE slug = 'my-custom' AND user_id = $1", user_b
            )
            == 1
        )
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM tags WHERE slug = 'my-custom' AND user_id = $1", user_a
            )
            == 1
        )
        revisions = await conn.fetch(
            "SELECT entity_type, payload FROM sync_revision_log WHERE user_id = $1", user_a
        )
        assert any(
            row["entity_type"] == "entry" and row["payload"]["note"] is None for row in revisions
        )
        assert any(row["entity_type"] == "tag" for row in revisions)
        await conn.execute("SET ROLE correlcore_app")
        await conn.execute("SELECT set_config('app.current_user_id', $1, false)", str(user_a))
        assert await conn.fetchval("SELECT count(*) FROM entries WHERE id = $1", visible) == 1
        assert await conn.fetchval("SELECT count(*) FROM entries WHERE user_id = $1", user_b) == 0
    finally:
        await conn.close()


@pytest.mark.parametrize("start", ["046", "047", "048"])
def test_upgrade_from_old_schema(start: str) -> None:
    if os.getenv("CORRELCORE_RUN_INTEGRATION") != "1":
        pytest.skip("requires PostgreSQL integration service")
    database = f"a01_{uuid.uuid4().hex[:16]}"
    asyncio.run(_create_database(database))
    try:
        _alembic(database, start)
        ids = asyncio.run(_seed(database))
        _alembic(database, "head")
        asyncio.run(_verify(database, ids))
        _alembic(database, "head")  # already-applied 049 is never replayed
    finally:
        asyncio.run(_drop_database(database))


def test_mid_backfill_failure_keeps_source_and_can_retry() -> None:
    if os.getenv("CORRELCORE_RUN_INTEGRATION") != "1":
        pytest.skip("requires PostgreSQL integration service")
    database = f"a01_{uuid.uuid4().hex[:16]}"
    asyncio.run(_create_database(database))
    try:
        _alembic(database, "048")
        ids = asyncio.run(_seed(database))
        user_b = ids[1]

        async def add_fault() -> None:
            conn = await asyncpg.connect(_url(database))
            try:
                await conn.execute(
                    "CREATE FUNCTION a01_fail_link() RETURNS trigger LANGUAGE plpgsql AS $$ "
                    "BEGIN IF NEW.user_id = '" + str(user_b) + "'::uuid THEN "
                    "RAISE EXCEPTION 'injected backfill failure'; END IF; RETURN NEW; END $$"
                )
                await conn.execute(
                    "CREATE TRIGGER a01_fail_link BEFORE INSERT ON entry_tags "
                    "FOR EACH ROW EXECUTE FUNCTION a01_fail_link()"
                )
            finally:
                await conn.close()

        asyncio.run(add_fault())
        _alembic(database, "head", succeeds=False)

        async def inspect_and_clear() -> None:
            conn = await asyncpg.connect(_url(database))
            try:
                assert await conn.fetchval("SELECT version_num FROM alembic_version") == "048"
                assert await conn.fetchval("SELECT count(*) FROM entry_note_markers") == 9
                assert await conn.fetchval("SELECT count(*) FROM entry_tags") == 50
                assert (
                    await conn.fetchval("SELECT count(*) FROM tags WHERE slug = 'co-llision'") == 0
                )
                await conn.execute("DROP TRIGGER a01_fail_link ON entry_tags")
                await conn.execute("DROP FUNCTION a01_fail_link()")
            finally:
                await conn.close()

        asyncio.run(inspect_and_clear())
        _alembic(database, "head")
        asyncio.run(_verify(database, ids))
    finally:
        asyncio.run(_drop_database(database))
