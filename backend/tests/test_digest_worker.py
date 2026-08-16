"""Unit tests for the weekly digest worker listing path."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.digest import _list_digest_user_ids


def _scalars_result(values: list[object]) -> MagicMock:
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


def _first_result(value: tuple[object, ...] | None) -> MagicMock:
    result = MagicMock()
    result.first.return_value = value
    return result


@pytest.mark.asyncio
async def test_list_digest_user_ids_binds_rls_before_reading_preferences() -> None:
    """``user_preferences`` is FORCE RLS; an unbound join hides every row.

    Production ``correlcore_app`` would otherwise return an empty eligible
    list every Sunday even when users have opted in.
    """
    opted_in = uuid.uuid4()
    opted_out = uuid.uuid4()
    no_prefs = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([opted_in, opted_out, no_prefs]),
            _first_result((True, True)),
            _first_result((True, False)),
            _first_result(None),
        ]
    )

    with patch("app.workers.digest.bind_rls_current_user", new=AsyncMock()) as bind_rls:
        eligible = await _list_digest_user_ids(db)

    assert eligible == [opted_in]
    assert [call.args for call in bind_rls.await_args_list] == [
        (db, opted_in),
        (db, opted_out),
        (db, no_prefs),
    ]
    list_stmt = db.execute.await_args_list[0].args[0]
    where_sql = str(list_stmt.whereclause)
    assert "users.is_active IS true" in where_sql
    assert "users.is_verified IS true" in where_sql
    assert "user_preferences" not in str(list_stmt)


@pytest.mark.asyncio
async def test_list_digest_user_ids_skips_analytics_opt_out() -> None:
    user_id = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([user_id]),
            _first_result((False, True)),
        ]
    )

    with patch("app.workers.digest.bind_rls_current_user", new=AsyncMock()):
        eligible = await _list_digest_user_ids(db)

    assert eligible == []
