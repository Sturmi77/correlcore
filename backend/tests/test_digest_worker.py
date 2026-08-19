"""Unit tests for the weekly digest worker listing path."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.digest import (
    _list_digest_user_ids,
    _parse_digest_cli,
    run_legacy_digest_container,
)


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


def test_digest_cli_requires_once_for_one_shot() -> None:
    """Bare ``python -m app.workers.digest`` is the leftover compose command."""

    assert _parse_digest_cli([]).once is False
    assert _parse_digest_cli(["--once"]).once is True


@pytest.mark.asyncio
async def test_legacy_digest_container_idles_without_generating() -> None:
    """Leftover digest-worker must not generate-and-exit (Docker restart loop)."""
    with (
        patch("app.workers.digest.run_digest_once", new=AsyncMock()) as generate,
        patch(
            "app.workers.digest.asyncio.sleep",
            new=AsyncMock(side_effect=asyncio.CancelledError),
        ) as sleep,
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_legacy_digest_container()

    generate.assert_not_called()
    sleep.assert_awaited_once()


def test_digest_main_without_once_idles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["digest"])
    with patch("app.workers.digest.asyncio.run") as run:
        from app.workers.digest import main

        main()

    run.assert_called_once()
    coro = run.call_args.args[0]
    assert coro.cr_code.co_name == "run_legacy_digest_container"
    coro.close()


def test_digest_main_once_generates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["digest", "--once"])
    with patch("app.workers.digest.asyncio.run") as run:
        from app.workers.digest import main

        main()

    run.assert_called_once()
    coro = run.call_args.args[0]
    assert coro.cr_code.co_name == "run_digest_once"
    coro.close()
