"""Unit tests for app.services.consent_service (Issue #31)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.consent_log import (
    CONSENT_TYPE_HEALTH_CONNECT,
    CURRENT_HEALTH_CONNECT_CONSENT_VERSION,
    ConsentLog,
)
from app.schemas.consent import ConsentRecordRequest
from app.services.consent_service import (
    is_consent_granted,
    list_consent_history,
    record_consent,
    revoke_consent,
    summarize_current_consents,
)
from tests.conftest import make_user


def _scalar_all_result(values: list[object]) -> MagicMock:
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


def _scalar_one_result(value: object | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_consent_log(
    *,
    user_id,
    consent_type: str = CONSENT_TYPE_HEALTH_CONNECT,
    consent_version: str = CURRENT_HEALTH_CONNECT_CONSENT_VERSION,
    granted: bool = True,
    created_at: datetime | None = None,
) -> ConsentLog:
    entry = ConsentLog()
    entry.id = uuid.uuid4()
    entry.user_id = user_id
    entry.consent_type = consent_type
    entry.consent_version = consent_version
    entry.granted = granted
    entry.created_at = created_at or datetime.now(UTC)
    return entry


@pytest.mark.asyncio
async def test_record_consent_appends_row() -> None:
    user = make_user()
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    out = await record_consent(
        db,
        user_id=user.id,
        payload=ConsentRecordRequest(
            type=CONSENT_TYPE_HEALTH_CONNECT,
            version=CURRENT_HEALTH_CONNECT_CONSENT_VERSION,
            granted=True,
        ),
    )

    assert out.user_id == user.id
    assert out.consent_type == CONSENT_TYPE_HEALTH_CONNECT
    assert out.granted is True
    db.add.assert_called_once()
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_consent_records_false_grant() -> None:
    user = make_user()
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    out = await revoke_consent(
        db,
        user_id=user.id,
        consent_type=CONSENT_TYPE_HEALTH_CONNECT,
        consent_version=CURRENT_HEALTH_CONNECT_CONSENT_VERSION,
    )

    assert out.granted is False
    assert out.consent_version == CURRENT_HEALTH_CONNECT_CONSENT_VERSION


def test_summarize_current_consents_uses_latest_event_per_type() -> None:
    user = make_user()
    older = _make_consent_log(
        user_id=user.id,
        granted=True,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    newer = _make_consent_log(
        user_id=user.id,
        granted=False,
        created_at=datetime(2026, 2, 1, tzinfo=UTC),
    )

    summary = summarize_current_consents([newer, older])

    assert len(summary) == 1
    assert summary[0].consent_type == CONSENT_TYPE_HEALTH_CONNECT
    assert summary[0].granted is False
    assert summary[0].updated_at == newer.created_at


@pytest.mark.asyncio
async def test_is_consent_granted_false_when_no_history() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_one_result(None))

    assert (
        await is_consent_granted(
            db,
            user_id=user.id,
            consent_type=CONSENT_TYPE_HEALTH_CONNECT,
        )
        is False
    )


@pytest.mark.asyncio
async def test_is_consent_granted_true_when_latest_grant() -> None:
    user = make_user()
    latest = _make_consent_log(user_id=user.id, granted=True)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_one_result(latest))

    assert (
        await is_consent_granted(
            db,
            user_id=user.id,
            consent_type=CONSENT_TYPE_HEALTH_CONNECT,
        )
        is True
    )


@pytest.mark.asyncio
async def test_list_consent_history_returns_rows_newest_first() -> None:
    user = make_user()
    rows = [
        _make_consent_log(user_id=user.id, granted=True),
        _make_consent_log(user_id=user.id, granted=False),
    ]
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_all_result(rows))

    out = await list_consent_history(db, user_id=user.id)

    assert out == rows
    db.execute.assert_awaited_once()
