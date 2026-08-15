"""Unit tests for app.services.user_service (Issue #66, SA-4).

Pure service-layer tests with mocked DB + TokenStore — no Postgres,
no Redis. The cascade reach itself is tested at the model layer via
``ondelete='CASCADE'`` declarations and is implicitly covered by every
endpoint test that creates and later deletes data; here we focus on
the service contract:

- Wrong password raises :class:`UserDeletionError` and **does not**
  touch the DB or the token store.
- Correct password revokes all refresh tokens **before** issuing the
  DELETE statement (so a partial failure leaves the user logged out).
- Logging never includes the user's email.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.security import hash_password
from app.services.user_service import UserDeletionError, delete_user_account, purge_user_account
from tests.conftest import make_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> MagicMock:
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


def _make_token_store() -> MagicMock:
    store = MagicMock()
    store.revoke_all = AsyncMock()
    store.revoke = AsyncMock()
    store.is_valid = AsyncMock()
    return store


@pytest.fixture(autouse=True)
def bind_rls() -> AsyncMock:
    """``purge_user_account`` rebinds RLS to the target; keep unit tests off the DB."""
    with patch("app.services.user_service.bind_rls_current_user", new_callable=AsyncMock) as mock:
        yield mock


# ---------------------------------------------------------------------------
# Wrong-password path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_user_wrong_password_raises_and_keeps_state() -> None:
    user = make_user(hashed_password=hash_password("correct-pw1"))
    db = _make_db()
    store = _make_token_store()

    with pytest.raises(UserDeletionError, match="Invalid credentials"):
        await delete_user_account(db, store, user, password="not-the-right-pw1")

    # Crucial: nothing was deleted, no tokens revoked.
    db.execute.assert_not_called()
    store.revoke_all.assert_not_called()


@pytest.mark.asyncio
async def test_delete_user_wrong_password_logs_user_id_not_email(
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = make_user(
        email="alice@example.com",
        hashed_password=hash_password("correct-pw1"),
    )
    db = _make_db()
    store = _make_token_store()

    with caplog.at_level(logging.WARNING, logger="app.services.user_service"):
        with pytest.raises(UserDeletionError):
            await delete_user_account(db, store, user, password="wrong-pw1")

    # Privacy invariant: the email must never end up in logs from this path.
    full_log = "\n".join(rec.getMessage() + str(rec.__dict__) for rec in caplog.records)
    assert "alice@example.com" not in full_log
    assert str(user.id) in full_log


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_user_happy_path_revokes_tokens_and_deletes() -> None:
    user = make_user(hashed_password=hash_password("correct-pw1"))
    db = _make_db()
    store = _make_token_store()

    await delete_user_account(db, store, user, password="correct-pw1")

    # Refresh tokens revoked once for this exact user_id.
    store.revoke_all.assert_awaited_once_with(str(user.id))

    # Exactly one DELETE statement issued against the users table.
    db.execute.assert_awaited_once()
    delete_stmt = db.execute.await_args.args[0]
    compiled = str(delete_stmt.compile(compile_kwargs={"literal_binds": False}))
    assert compiled.startswith("DELETE FROM users")


@pytest.mark.asyncio
async def test_delete_user_revokes_tokens_before_deleting_row(bind_rls: AsyncMock) -> None:
    """Order matters — even on a later DB failure the user is logged out.

    RLS is rebound to the target after revoke and before DELETE so an admin
    actor's GUC cannot hide the target's FORCE-RLS children from CASCADE.
    """
    user = make_user(hashed_password=hash_password("correct-pw1"))
    db = _make_db()
    store = _make_token_store()

    call_order: list[str] = []

    async def _track_revoke(_uid: str) -> None:
        call_order.append("revoke_all")

    async def _track_bind(_db: object, _user_id: object) -> None:
        call_order.append("bind_rls")

    async def _track_execute(*_a: object, **_kw: object) -> None:
        call_order.append("delete")

    store.revoke_all = AsyncMock(side_effect=_track_revoke)
    bind_rls.side_effect = _track_bind
    db.execute = AsyncMock(side_effect=_track_execute)

    await delete_user_account(db, store, user, password="correct-pw1")

    assert call_order == ["revoke_all", "bind_rls", "delete"]
    bind_rls.assert_awaited_once_with(db, user.id)


@pytest.mark.asyncio
async def test_delete_user_happy_path_logs_user_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = make_user(
        email="bob@example.com",
        hashed_password=hash_password("correct-pw1"),
    )
    db = _make_db()
    store = _make_token_store()

    with caplog.at_level(logging.INFO, logger="app.services.user_service"):
        await delete_user_account(db, store, user, password="correct-pw1")

    success_records = [r for r in caplog.records if r.levelno == logging.INFO]
    assert success_records, "expected an INFO log entry on success"
    full_log = "\n".join(r.getMessage() + str(r.__dict__) for r in success_records)
    assert str(user.id) in full_log
    # Privacy invariant: email must not be logged.
    assert "bob@example.com" not in full_log


# ---------------------------------------------------------------------------
# Empty / no-op token store path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_user_revoke_all_is_called_even_with_no_active_sessions() -> None:
    """``revoke_all`` is a no-op when the user has no live tokens — the
    service must still call it so the contract stays simple."""
    user = make_user(hashed_password=hash_password("correct-pw1"))
    db = _make_db()
    store = _make_token_store()
    # Simulate ``revoke_all`` being called with zero matching keys — it
    # returns None either way, but we want to assert it *was* called.
    store.revoke_all = AsyncMock(return_value=None)

    await delete_user_account(db, store, user, password="correct-pw1")

    store.revoke_all.assert_awaited_once_with(str(user.id))
    db.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# Admin / cross-user purge must rebind RLS to the target
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purge_binds_rls_to_target_before_delete(bind_rls: AsyncMock) -> None:
    """Admin DELETE /users/{id} runs under the actor's ``app.current_user_id``.

    Without rebinding, FORCE RLS hides the target's ``user_encryption_keys``
    (and every other cascaded child) from ``correlcore_app``. The FK check
    still sees those rows, so the wipe raises IntegrityError and 500s.
    """
    user = make_user()
    db = _make_db()
    store = _make_token_store()

    await purge_user_account(db, store, user)

    bind_rls.assert_awaited_once_with(db, user.id)
    store.revoke_all.assert_awaited_once_with(str(user.id))
    db.execute.assert_awaited_once()
    delete_stmt = db.execute.await_args.args[0]
    compiled = str(delete_stmt.compile(compile_kwargs={"literal_binds": False}))
    assert compiled.startswith("DELETE FROM users")
