"""Tests for the admin console API (#677 P2).

The ``require_admin`` gate is exercised end-to-end by overriding
``get_current_verified_user`` (so the *real* ``require_admin`` runs against the
returned user). Service-layer functions are patched with ``AsyncMock`` so these
stay endpoint/contract tests — the deeper query/cascade behaviour lives in the
service and migration tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.user import User
from tests.conftest import make_user

# Every route lives under this prefix (see app/api/v1/router.py).
BASE = "/api/v1/admin"
COOKIES = {"access_token": "valid.access.token"}


def _override_current_user(u: User) -> None:
    async def override() -> User:
        return u

    app.dependency_overrides[get_current_verified_user] = override


@pytest.fixture(autouse=True)
def _clear_overrides_and_limiter():
    from app.core.rate_limit import limiter

    limiter.reset()
    yield
    app.dependency_overrides.clear()
    limiter.reset()


# --------------------------------------------------------------------------- #
# require_admin gate — non-admins are rejected on every route (403).
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_non_admin_forbidden_on_every_route(async_client: AsyncClient) -> None:
    _override_current_user(make_user(admin=False))
    target = uuid.uuid4()

    calls = [
        async_client.get(f"{BASE}/users", cookies=COOKIES),
        async_client.get(f"{BASE}/users/{target}", cookies=COOKIES),
        async_client.patch(f"{BASE}/users/{target}/active", json={"is_active": False}, cookies=COOKIES),
        async_client.delete(f"{BASE}/users/{target}", cookies=COOKIES),
        async_client.post(f"{BASE}/users/{target}/password-reset", cookies=COOKIES),
    ]
    for coro in calls:
        r = await coro
        assert r.status_code == 403, r.text


# --------------------------------------------------------------------------- #
# GET /users — list + search.
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_list_users(async_client: AsyncClient) -> None:
    _override_current_user(make_user(admin=True, email="admin@example.com"))
    listed = [make_user(email="a@example.com"), make_user(email="b@example.com")]

    with patch(
        "app.services.admin_service.list_users",
        new_callable=AsyncMock,
        return_value=(listed, 2),
    ) as mock_list:
        r = await async_client.get(f"{BASE}/users?query=example&active=true&limit=25", cookies=COOKIES)

    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert body["limit"] == 25
    assert len(body["items"]) == 2
    # Filters are forwarded to the service.
    _, kwargs = mock_list.call_args
    assert kwargs["query"] == "example"
    assert kwargs["active"] is True
    assert kwargs["limit"] == 25


@pytest.mark.asyncio
async def test_list_users_limit_over_max_rejected(async_client: AsyncClient) -> None:
    _override_current_user(make_user(admin=True))
    r = await async_client.get(f"{BASE}/users?limit=1000", cookies=COOKIES)
    assert r.status_code == 422  # exceeds MAX_ADMIN_PAGE (le=100)


# --------------------------------------------------------------------------- #
# GET /users/{id} — detail with entry_count.
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_get_user_detail_includes_entry_count(async_client: AsyncClient) -> None:
    _override_current_user(make_user(admin=True))
    target = make_user(email="target@example.com")

    with patch(
        "app.api.v1.endpoints.admin.admin_service.get_user_with_entry_count",
        new_callable=AsyncMock,
        return_value=(target, 42),
    ):
        r = await async_client.get(f"{BASE}/users/{target.id}", cookies=COOKIES)

    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "target@example.com"
    assert body["entry_count"] == 42


@pytest.mark.asyncio
async def test_get_user_detail_404(async_client: AsyncClient) -> None:
    _override_current_user(make_user(admin=True))
    with patch(
        "app.api.v1.endpoints.admin.admin_service.get_user_with_entry_count",
        new_callable=AsyncMock,
        return_value=None,
    ):
        r = await async_client.get(f"{BASE}/users/{uuid.uuid4()}", cookies=COOKIES)
    assert r.status_code == 404


# --------------------------------------------------------------------------- #
# PATCH /users/{id}/active — disable / enable + audit.
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_disable_user_records_audit(async_client: AsyncClient) -> None:
    _override_current_user(make_user(admin=True, email="admin@example.com"))
    target = make_user(email="target@example.com")

    with (
        patch(
            "app.api.v1.endpoints.admin.admin_service.get_user_with_entry_count",
            new_callable=AsyncMock,
            return_value=(target, 3),
        ),
        patch(
            "app.api.v1.endpoints.admin.admin_service.set_user_active",
            new_callable=AsyncMock,
        ) as mock_set,
        patch(
            "app.api.v1.endpoints.admin.admin_service.record_admin_action",
            new_callable=AsyncMock,
        ) as mock_audit,
    ):
        r = await async_client.patch(
            f"{BASE}/users/{target.id}/active", json={"is_active": False}, cookies=COOKIES
        )

    assert r.status_code == 200
    mock_set.assert_awaited_once()
    assert mock_set.call_args.kwargs["is_active"] is False
    mock_audit.assert_awaited_once()
    assert mock_audit.call_args.kwargs["action"] == "disable_user"


@pytest.mark.asyncio
async def test_cannot_disable_self(async_client: AsyncClient) -> None:
    admin = make_user(admin=True, email="admin@example.com")
    _override_current_user(admin)

    with patch(
        "app.api.v1.endpoints.admin.admin_service.get_user_with_entry_count",
        new_callable=AsyncMock,
        return_value=(admin, 0),
    ):
        r = await async_client.patch(
            f"{BASE}/users/{admin.id}/active", json={"is_active": False}, cookies=COOKIES
        )
    assert r.status_code == 400


# --------------------------------------------------------------------------- #
# DELETE /users/{id} — hard delete, audit-before-purge, self-guard.
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_delete_user_purges_and_audits(async_client: AsyncClient) -> None:
    _override_current_user(make_user(admin=True, email="admin@example.com"))
    target = make_user(email="target@example.com")

    with (
        patch(
            "app.api.v1.endpoints.admin.admin_service.get_user_with_entry_count",
            new_callable=AsyncMock,
            return_value=(target, 0),
        ),
        patch(
            "app.api.v1.endpoints.admin.admin_service.record_admin_action",
            new_callable=AsyncMock,
        ) as mock_audit,
        patch(
            "app.api.v1.endpoints.admin.purge_user_account",
            new_callable=AsyncMock,
        ) as mock_purge,
    ):
        r = await async_client.delete(f"{BASE}/users/{target.id}", cookies=COOKIES)

    assert r.status_code == 204
    mock_audit.assert_awaited_once()
    assert mock_audit.call_args.kwargs["action"] == "delete_user"
    mock_purge.assert_awaited_once()


@pytest.mark.asyncio
async def test_cannot_delete_self(async_client: AsyncClient) -> None:
    admin = make_user(admin=True, email="admin@example.com")
    _override_current_user(admin)

    with (
        patch(
            "app.api.v1.endpoints.admin.admin_service.get_user_with_entry_count",
            new_callable=AsyncMock,
            return_value=(admin, 0),
        ),
        patch(
            "app.api.v1.endpoints.admin.purge_user_account",
            new_callable=AsyncMock,
        ) as mock_purge,
    ):
        r = await async_client.delete(f"{BASE}/users/{admin.id}", cookies=COOKIES)

    assert r.status_code == 400
    mock_purge.assert_not_awaited()


# --------------------------------------------------------------------------- #
# POST /users/{id}/password-reset — trigger the self-service reset email.
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_password_reset_sends_email_and_audits(async_client: AsyncClient) -> None:
    _override_current_user(make_user(admin=True, email="admin@example.com"))
    target = make_user(email="target@example.com")

    with (
        patch(
            "app.api.v1.endpoints.admin.admin_service.get_user_with_entry_count",
            new_callable=AsyncMock,
            return_value=(target, 0),
        ),
        patch(
            "app.api.v1.endpoints.admin.request_password_reset",
            new_callable=AsyncMock,
            return_value=(target, "plaintext-token"),
        ),
        patch("app.api.v1.endpoints.admin.send_password_reset_email") as mock_email,
        patch(
            "app.api.v1.endpoints.admin.admin_service.record_admin_action",
            new_callable=AsyncMock,
        ) as mock_audit,
    ):
        r = await async_client.post(f"{BASE}/users/{target.id}/password-reset", cookies=COOKIES)

    assert r.status_code == 202
    mock_audit.assert_awaited_once()
    assert mock_audit.call_args.kwargs["action"] == "trigger_password_reset"
    # Email is dispatched via BackgroundTasks after the response.
    mock_email.assert_called_once()


@pytest.mark.asyncio
async def test_password_reset_conflict_for_inactive_user(async_client: AsyncClient) -> None:
    _override_current_user(make_user(admin=True))
    target = make_user(active=False, email="inactive@example.com")

    with (
        patch(
            "app.api.v1.endpoints.admin.admin_service.get_user_with_entry_count",
            new_callable=AsyncMock,
            return_value=(target, 0),
        ),
        patch(
            "app.api.v1.endpoints.admin.request_password_reset",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.api.v1.endpoints.admin.admin_service.record_admin_action",
            new_callable=AsyncMock,
        ) as mock_audit,
    ):
        r = await async_client.post(f"{BASE}/users/{target.id}/password-reset", cookies=COOKIES)

    assert r.status_code == 409
    mock_audit.assert_not_awaited()
