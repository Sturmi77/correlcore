"""Integration smoke for the M7 QA seed against real PostgreSQL + pgvector.

Opt-in locally: set ``CORRELCORE_RUN_INTEGRATION=1`` after migrations and
service containers are up. CI runs this in the ``migrations-smoke`` job.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import select

from app.core.crypto import reset_current_user_dek, set_current_user_dek, unwrap_dek
from app.db.session import AsyncSessionLocal, bind_rls_current_user
from app.models.insight import InsightType
from app.models.user_encryption_key import UserEncryptionKey
from app.services.insight_service import list_latest_insights
from app.services.m7_qa_seed_service import (
    M7_QA_DEFAULT_DAYS,
    M7_QA_DEFAULT_EMAIL,
    M7_QA_DEFAULT_PASSWORD,
    seed_m7_qa_dataset,
)
from app.services.multivariate_analytics import MIN_ML_ENTRIES
from app.services.stats_service import get_symptom_tag_cooccurrence
from app.services.tag_cluster_service import get_tag_clusters


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
async def test_m7_qa_seed_generates_lasso_lag_symptom_and_tag_clusters() -> None:
    if not _integration_enabled():
        pytest.skip("requires real PostgreSQL with pgvector (CORRELCORE_RUN_INTEGRATION=1)")

    integration_email = f"m7-integration-{uuid.uuid4().hex[:8]}@localhost.dev"

    async with AsyncSessionLocal() as session:
        summary = await seed_m7_qa_dataset(
            session,
            email=integration_email,
            password=M7_QA_DEFAULT_PASSWORD,
            day_count=M7_QA_DEFAULT_DAYS,
            reset=True,
        )
        await session.commit()

    assert summary.entry_count >= MIN_ML_ENTRIES
    assert summary.has_lasso_or_lag
    assert summary.has_symptom_insights
    assert summary.insight_counts_by_type.get(InsightType.SYMPTOM_MOOD_ASSOCIATION.value, 0) > 0
    assert summary.insight_counts_by_type.get(InsightType.SYMPTOM_TAG_COOCCURRENCE.value, 0) > 0

    async with AsyncSessionLocal() as session:
        await bind_rls_current_user(session, summary.user_id)
        key_result = await session.execute(
            select(UserEncryptionKey.wrapped_dek).where(
                UserEncryptionKey.user_id == summary.user_id
            )
        )
        wrapped_dek = key_result.scalar_one()
        dek_token = set_current_user_dek(summary.user_id, unwrap_dek(wrapped_dek))
        try:
            latest = await list_latest_insights(session, user_id=summary.user_id, limit=50)
            insight_types = {insight.insight_type for insight in latest}
            assert InsightType.SYMPTOM_CLUSTER in insight_types

            clusters = await get_tag_clusters(session, user_id=summary.user_id)
            assert clusters.status == "ok"
            assert clusters.entry_count >= MIN_ML_ENTRIES
            assert clusters.active_tag_count >= 5
            assert len(clusters.clusters) >= 1

            cooccurrence = await get_symptom_tag_cooccurrence(
                session,
                user_id=summary.user_id,
                range_="90d",
            )
            assert len(cooccurrence.cells) >= 1
        finally:
            reset_current_user_dek(dek_token)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_m7_qa_seed_is_idempotent_with_reset() -> None:
    if not _integration_enabled():
        pytest.skip("requires real PostgreSQL with pgvector (CORRELCORE_RUN_INTEGRATION=1)")

    async with AsyncSessionLocal() as session:
        first = await seed_m7_qa_dataset(
            session,
            email=M7_QA_DEFAULT_EMAIL,
            password=M7_QA_DEFAULT_PASSWORD,
            reset=True,
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        second = await seed_m7_qa_dataset(
            session,
            email=M7_QA_DEFAULT_EMAIL,
            password=M7_QA_DEFAULT_PASSWORD,
            reset=True,
        )
        await session.commit()

    assert first.entry_count == second.entry_count == M7_QA_DEFAULT_DAYS
    assert first.has_lasso_or_lag and second.has_lasso_or_lag
