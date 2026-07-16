"""Tests for O-20 — password reset flow."""

from __future__ import annotations

import asyncio
import os
import uuid
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql

from app.core.security import verify_password
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.auth_service import (
    PasswordResetError,
    _hash_token,
    request_password_reset,
    reset_password,
)
from tests.conftest import (
    NEW_TEST_PASSWORD,
    VALID_ACCESS_TOKEN,
    VALID_REFRESH_TOKEN,
    make_db_session_with_results,
    make_password_reset_token,
    make_user,
)


@pytest.mark.asyncio
async def test_request_password_reset_unknown_email_returns_none() -> None:
    db = make_db_session_with_results(None)
    result = await request_password_reset(db, "missing@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_request_password_reset_unverified_user_skipped() -> None:
    user = make_user(verified=False)
    db = make_db_session_with_results(user)
    result = await request_password_reset(db, user.email)
    assert result is None


@pytest.mark.asyncio
async def test_request_password_reset_inactive_user_skipped() -> None:
    user = make_user(active=False)
    db = make_db_session_with_results(user)
    result = await request_password_reset(db, user.email)
    assert result is None


@pytest.mark.asyncio
async def test_reset_password_unknown_token_raises_generic() -> None:
    db = make_db_session_with_results(None)
    with pytest.raises(PasswordResetError, match="Invalid or expired"):
        await reset_password(db, "unknown-token", NEW_TEST_PASSWORD)


@pytest.mark.asyncio
async def test_reset_password_expired_token_raises_generic() -> None:
    user = make_user()
    record, plaintext = make_password_reset_token(user, expires_in=timedelta(hours=-1))
    db = make_db_session_with_results(record)
    with pytest.raises(PasswordResetError, match="Invalid or expired"):
        await reset_password(db, plaintext, NEW_TEST_PASSWORD)


@pytest.mark.asyncio
async def test_reset_password_used_token_raises_generic() -> None:
    user = make_user()
    record, plaintext = make_password_reset_token(user, used=True)
    db = make_db_session_with_results(record)
    with pytest.raises(PasswordResetError, match="Invalid or expired"):
        await reset_password(db, plaintext, NEW_TEST_PASSWORD)


@pytest.mark.asyncio
async def test_reset_password_success_updates_hash() -> None:
    user = make_user()
    record, plaintext = make_password_reset_token(user)
    db = make_db_session_with_results(record, user, None)
    returned = await reset_password(db, plaintext, NEW_TEST_PASSWORD)
    assert returned is user
    assert verify_password(NEW_TEST_PASSWORD, user.hashed_password)
    assert record.used_at is not None
    select_statement = db.execute.await_args_list[0].args[0]
    compiled_select = str(select_statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in compiled_select
    delete_statement = db.execute.await_args_list[2].args[0]
    assert "DELETE FROM password_reset_tokens" in str(delete_statement)
    assert "password_reset_tokens.user_id" in str(delete_statement)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reset_password_concurrent_same_token_is_single_use_on_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if os.getenv("CORRELCORE_RUN_INTEGRATION") != "1":
        pytest.skip("requires real PostgreSQL (CORRELCORE_RUN_INTEGRATION=1)")

    import app.services.auth_service as auth_service
    from app.db.session import AsyncSessionLocal

    plaintext = f"reset-token-{uuid.uuid4().hex}"
    user_id = uuid.uuid4()
    email = f"reset-race-{uuid.uuid4().hex[:12]}@example.test"

    async with AsyncSessionLocal() as session:
        session.add(
            User(
                id=user_id,
                email=email,
                hashed_password="hashed::old",
                display_name="Reset Race",
                is_active=True,
                is_verified=True,
            )
        )
        session.add(
            PasswordResetToken(
                id=uuid.uuid4(),
                user_id=user_id,
                token_hash=_hash_token(plaintext),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        await session.commit()

    original_get_user_by_id = auth_service._get_user_by_id
    selected_count = 0
    selected_lock = asyncio.Lock()
    two_transactions_selected = asyncio.Event()

    async def gated_get_user_by_id(db, requested_user_id):  # type: ignore[no-untyped-def]
        nonlocal selected_count
        async with selected_lock:
            selected_count += 1
            if selected_count == 2:
                two_transactions_selected.set()
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(two_transactions_selected.wait(), timeout=0.25)
        return await original_get_user_by_id(db, requested_user_id)

    monkeypatch.setattr(auth_service, "_get_user_by_id", gated_get_user_by_id)
    monkeypatch.setattr(auth_service, "hash_password", lambda password: f"hashed::{password}")

    async def attempt(new_password: str) -> tuple[str, str]:
        async with AsyncSessionLocal() as session:
            try:
                await reset_password(session, plaintext, new_password)
            except PasswordResetError as exc:
                await session.rollback()
                return ("error", str(exc))
            await session.commit()
            return ("ok", new_password)

    try:
        results = await asyncio.gather(attempt("VictimPass1"), attempt("AttackerPass1"))

        successes = [password for status, password in results if status == "ok"]
        errors = [message for status, message in results if status == "error"]
        assert len(successes) == 1
        assert errors == ["Invalid or expired password reset token"]

        async with AsyncSessionLocal() as session:
            persisted_user = await session.get(User, user_id)
            remaining_tokens = await session.scalar(
                select(func.count(PasswordResetToken.id)).where(
                    PasswordResetToken.user_id == user_id
                )
            )

        assert persisted_user is not None
        assert persisted_user.hashed_password == f"hashed::{successes[0]}"
        assert remaining_tokens == 0
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                PasswordResetToken.__table__.delete().where(PasswordResetToken.user_id == user_id)
            )
            await session.execute(User.__table__.delete().where(User.id == user_id))
            await session.commit()


@pytest.mark.asyncio
async def test_endpoint_forgot_password_always_202(async_client: AsyncClient) -> None:
    with patch(
        "app.api.v1.endpoints.auth.request_password_reset",
        new_callable=AsyncMock,
        return_value=None,
    ):
        r = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "user@example.com"},
        )
    assert r.status_code == 202
    assert "password reset mail" in r.json()["message"]


@pytest.mark.asyncio
async def test_endpoint_forgot_password_schedules_mail(async_client: AsyncClient) -> None:
    user = make_user()
    plaintext = "x" * 32
    with (
        patch(
            "app.api.v1.endpoints.auth.request_password_reset",
            new_callable=AsyncMock,
            return_value=(user, plaintext),
        ),
        patch(
            "app.api.v1.endpoints.auth.send_password_reset_email",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        r = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": user.email},
        )
    assert r.status_code == 202
    mock_send.assert_awaited()


@pytest.mark.asyncio
async def test_endpoint_reset_password_success(async_client: AsyncClient) -> None:
    user = make_user()
    with (
        patch(
            "app.api.v1.endpoints.auth.reset_password",
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            "app.api.v1.endpoints.auth.TokenStore.revoke_all",
            new_callable=AsyncMock,
        ) as mock_revoke,
        patch(
            "app.api.v1.endpoints.auth.issue_session_tokens",
            new_callable=AsyncMock,
            return_value=(VALID_ACCESS_TOKEN, VALID_REFRESH_TOKEN),
        ),
    ):
        r = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": "x" * 32, "password": NEW_TEST_PASSWORD},
        )
    assert r.status_code == 200
    mock_revoke.assert_awaited_once_with(str(user.id))
    assert "access_token" not in r.json()
    assert "access_token" in r.cookies
    assert "refresh_token" in r.cookies


@pytest.mark.asyncio
async def test_endpoint_reset_password_invalid_no_cookies(async_client: AsyncClient) -> None:
    with patch(
        "app.api.v1.endpoints.auth.reset_password",
        new_callable=AsyncMock,
        side_effect=PasswordResetError("Invalid or expired password reset token"),
    ):
        r = await async_client.post(
            "/api/v1/auth/reset-password",
            json={"token": "x" * 32, "password": NEW_TEST_PASSWORD},
        )
    assert r.status_code == 400
    assert "access_token" not in r.cookies
    assert "refresh_token" not in r.cookies


@pytest.mark.asyncio
async def test_endpoint_reset_password_weak_password_validation(async_client: AsyncClient) -> None:
    r = await async_client.post(
        "/api/v1/auth/reset-password",
        json={"token": "x" * 32, "password": "short"},
    )
    assert r.status_code == 422
