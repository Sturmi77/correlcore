"""GDPR account-delete cascade against real PostgreSQL.

Verifies Art. 17 hard-delete removes owned rows (entries, insights, DEK)
via ON DELETE CASCADE when ``purge_user_account`` runs under the correct
RLS bind. Opt-in: ``CORRELCORE_RUN_INTEGRATION=1`` after migrations.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import func, select, text

from app.db.session import AsyncSessionLocal, bind_rls_current_user
from app.models.entry import Entry, EntrySlot, EntrySource, WorkContext
from app.models.insight import Insight, InsightTier, InsightType
from app.models.user import User
from app.models.user_encryption_key import UserEncryptionKey
from app.schemas.auth import RegisterRequest
from app.services.auth_service import register_user
from app.services.user_service import delete_user_account


@pytest.fixture(autouse=True)
async def dispose_async_engine_after_integration_test() -> None:
    yield
    from app.db.session import engine

    await engine.dispose()


def _integration_enabled() -> bool:
    return os.getenv("CORRELCORE_RUN_INTEGRATION") == "1"


def _token_store() -> MagicMock:
    store = MagicMock()
    store.revoke_all = AsyncMock()
    return store


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_user_account_cascades_entries_insights_and_dek() -> None:
    if not _integration_enabled():
        pytest.skip("requires PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    email = f"gdpr-del-{uuid.uuid4().hex[:8]}@localhost.dev"
    password = "test-password-12"

    async with AsyncSessionLocal() as session:
        user = await register_user(
            session,
            RegisterRequest(email=email, password=password, display_name="GDPR"),
        )
        user.is_verified = True
        await session.commit()
        user_id = user.id

    entry_id = uuid.uuid4()
    insight_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        await bind_rls_current_user(session, user_id)
        session.add(
            Entry(
                id=entry_id,
                user_id=user_id,
                entry_date=date(2026, 9, 2),
                slot=EntrySlot.DAY,
                mood_score=3,
                energy=3,
                stress=3,
                source=EntrySource.DIRECT,
                work_context=WorkContext.OFFICE,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        session.add(
            Insight(
                id=insight_id,
                user_id=user_id,
                insight_type=InsightType.WEEKDAY_PATTERN,
                tier=InsightTier.EARLY,
                metric="mood_score",
                sample_n=8,
                flags={},
                payload={"test": True},
                generated_for_date=date(2026, 9, 2),
                generated_at=datetime.now(UTC),
            )
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        await bind_rls_current_user(session, user_id)
        assert (
            await session.execute(select(func.count()).select_from(Entry))
        ).scalar_one() == 1
        assert (
            await session.execute(select(func.count()).select_from(Insight))
        ).scalar_one() == 1
        assert (
            await session.execute(
                select(func.count())
                .select_from(UserEncryptionKey)
                .where(UserEncryptionKey.user_id == user_id)
            )
        ).scalar_one() == 1

        db_user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one()
        await delete_user_account(session, _token_store(), db_user, password)
        await session.commit()

    async with AsyncSessionLocal() as session:
        await session.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user_id)},
        )
        assert (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none() is None
        assert (
            await session.execute(select(Entry).where(Entry.id == entry_id))
        ).scalar_one_or_none() is None
        assert (
            await session.execute(select(Insight).where(Insight.id == insight_id))
        ).scalar_one_or_none() is None
        assert (
            await session.execute(
                select(UserEncryptionKey).where(UserEncryptionKey.user_id == user_id)
            )
        ).scalar_one_or_none() is None
