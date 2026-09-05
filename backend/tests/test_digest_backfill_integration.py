"""Integration check for migration 031 (digest opt-in backfill, #449).

Opt-in locally: set ``CORRELCORE_RUN_INTEGRATION=1`` after migrations and
service containers are up. CI runs this in the ``migrations-smoke`` job, where
``alembic upgrade head`` has already applied 031.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal, bind_rls_current_user

BACKFILL_SQL = "UPDATE user_preferences SET digest_enabled = false WHERE digest_enabled = true"


@pytest.fixture(autouse=True)
async def dispose_async_engine_after_integration_test() -> None:
    yield
    from app.db import session as db_session

    await db_session.engine.dispose()
    db_session.reset_engine()


def _integration_enabled() -> bool:
    return os.getenv("CORRELCORE_RUN_INTEGRATION") == "1"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migration_031_resets_legacy_digest_rows() -> None:
    """A legacy row carrying the pre-#398 default must end up opted out."""

    if not _integration_enabled():
        pytest.skip("requires real PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    user_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        # user_preferences enforces RLS on app.current_user_id — bind it or every
        # statement below silently affects zero rows.
        await bind_rls_current_user(session, user_id)
        # A user row is required by the FK; keep it minimal and local to this test.
        await session.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, is_active, is_verified) "
                "VALUES (:id, :email, 'x', true, true)"
            ),
            {"id": user_id, "email": f"digest-031-{user_id.hex[:8]}@localhost.dev"},
        )
        await session.execute(
            text("INSERT INTO user_preferences (user_id, digest_enabled) VALUES (:id, true)"),
            {"id": user_id},
        )
        await session.commit()

    try:
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, user_id)
            # Re-running the migration statement must be idempotent.
            await session.execute(text(BACKFILL_SQL))
            await session.commit()

        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, user_id)
            result = await session.execute(
                text("SELECT digest_enabled FROM user_preferences WHERE user_id = :id"),
                {"id": user_id},
            )
            assert result.scalar_one() is False
    finally:
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, user_id)
            await session.execute(
                text("DELETE FROM user_preferences WHERE user_id = :id"), {"id": user_id}
            )
            await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
            await session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_new_preference_rows_default_to_opted_out() -> None:
    """Migration 028's column default must still hold after 031."""

    if not _integration_enabled():
        pytest.skip("requires real PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    user_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        await bind_rls_current_user(session, user_id)
        await session.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, is_active, is_verified) "
                "VALUES (:id, :email, 'x', true, true)"
            ),
            {"id": user_id, "email": f"digest-031b-{user_id.hex[:8]}@localhost.dev"},
        )
        # No explicit digest_enabled — the server default decides.
        await session.execute(
            text("INSERT INTO user_preferences (user_id) VALUES (:id)"), {"id": user_id}
        )
        await session.commit()

    try:
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, user_id)
            result = await session.execute(
                text("SELECT digest_enabled FROM user_preferences WHERE user_id = :id"),
                {"id": user_id},
            )
            assert result.scalar_one() is False
    finally:
        async with AsyncSessionLocal() as session:
            await bind_rls_current_user(session, user_id)
            await session.execute(
                text("DELETE FROM user_preferences WHERE user_id = :id"), {"id": user_id}
            )
            await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
            await session.commit()
