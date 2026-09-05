"""RLS isolation against real PostgreSQL as ``correlcore_app``.

The migration/owner role used by CI (``POSTGRES_USER=correlcore``) is a
superuser and bypasses RLS. This suite creates/uses the restricted
``correlcore_app`` role (same as production API) so FORCE RLS policies apply.

Opt-in: ``CORRELCORE_RUN_INTEGRATION=1`` after ``alembic upgrade head``.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select, text

from app.db.session import AsyncSessionLocal, bind_rls_current_user
from app.models.entry import Entry, EntrySlot, EntrySource, WorkContext
from app.schemas.auth import RegisterRequest
from app.services.auth_service import register_user

_APP_ROLE = "correlcore_app"


def _integration_enabled() -> bool:
    return os.getenv("CORRELCORE_RUN_INTEGRATION") == "1"


async def _ensure_app_role() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                f"""
                DO $$ BEGIN
                  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{_APP_ROLE}') THEN
                    CREATE ROLE {_APP_ROLE} NOINHERIT LOGIN PASSWORD 'correlcore_app';
                  END IF;
                END $$;
                """
            )
        )
        await session.execute(text(f"GRANT USAGE ON SCHEMA public TO {_APP_ROLE}"))
        await session.execute(
            text(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
                f"TO {_APP_ROLE}"
            )
        )
        await session.execute(
            text(f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {_APP_ROLE}")
        )
        await session.commit()


async def _register(email: str):
    async with AsyncSessionLocal() as session:
        user = await register_user(
            session,
            RegisterRequest(email=email, password="test-password-12", display_name="RLS"),
        )
        user.is_verified = True
        await session.commit()
        return user.id


async def _as_app_role(session) -> None:
    await session.execute(text(f"SET LOCAL ROLE {_APP_ROLE}"))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rls_user_cannot_read_another_users_entries() -> None:
    if not _integration_enabled():
        pytest.skip("requires PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    await _ensure_app_role()

    owner_id = await _register(f"rls-owner-{uuid.uuid4().hex[:8]}@localhost.dev")
    other_id = await _register(f"rls-other-{uuid.uuid4().hex[:8]}@localhost.dev")
    entry_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        await _as_app_role(session)
        await bind_rls_current_user(session, owner_id)
        session.add(
            Entry(
                id=entry_id,
                user_id=owner_id,
                entry_date=date(2026, 9, 1),
                slot=EntrySlot.DAY,
                mood_score=4,
                energy=3,
                stress=2,
                source=EntrySource.DIRECT,
                work_context=WorkContext.HOMEOFFICE,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        await _as_app_role(session)
        await bind_rls_current_user(session, owner_id)
        owned = (
            await session.execute(select(Entry).where(Entry.id == entry_id))
        ).scalar_one_or_none()
        assert owned is not None
        assert owned.user_id == owner_id

    async with AsyncSessionLocal() as session:
        await _as_app_role(session)
        await bind_rls_current_user(session, other_id)
        leaked = (
            await session.execute(select(Entry).where(Entry.id == entry_id))
        ).scalar_one_or_none()
        assert leaked is None
        count = (await session.execute(select(func.count()).select_from(Entry))).scalar_one()
        assert count == 0
