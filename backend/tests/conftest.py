"""Shared test fixtures and factories.

Centralises object construction and async-client setup that was previously
copied across ``test_auth.py`` and ``test_email_verification.py``. Keeping
factories in one place pays off as soon as M1 tests for entries / tags /
symptoms land — every new test file should reach for these helpers
instead of rolling its own ``_make_user``.

Conventions
-----------
- All factories accept keyword-only overrides so call sites stay readable
  even when only one attribute changes (e.g. ``make_user(verified=True)``).
- Factories never touch the database; they build detached SQLAlchemy
  instances suitable for ``MagicMock``-based service tests.
- ``async_test_client`` is the single canonical way to drive the FastAPI
  app in tests via ``httpx.AsyncClient`` + ``ASGITransport``.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.email_verification_token import EmailVerificationToken
from app.models.user import User
from app.services.auth_service import _hash_token

# ---------------------------------------------------------------------------
# Object factories
# ---------------------------------------------------------------------------


def make_user(
    *,
    verified: bool = True,
    active: bool = True,
    email: str = "test@example.com",
    display_name: str | None = "Test User",
    hashed_password: str = "$2b$12$placeholder",
) -> User:
    """Build a detached :class:`User` for service-layer tests.

    The default user is verified+active so endpoint tests don't need to
    repeat the boilerplate. Pass ``verified=False`` for the email-flow
    tests and ``active=False`` for the disabled-account paths.
    """
    u = User()
    u.id = uuid.uuid4()
    u.email = email
    u.hashed_password = hashed_password
    u.display_name = display_name
    u.is_active = active
    u.is_verified = verified
    u.created_at = datetime.now(UTC)
    u.updated_at = datetime.now(UTC)
    return u


def make_verification_token(
    user: User,
    *,
    plaintext: str | None = None,
    expires_in: timedelta = timedelta(hours=1),
    used: bool = False,
) -> tuple[EmailVerificationToken, str]:
    """Build a :class:`EmailVerificationToken` paired with its plaintext.

    Returns ``(record, plaintext)`` so tests can assert on the hashed
    record while still feeding the plaintext into the service.
    """
    plaintext = plaintext or secrets.token_urlsafe(32)
    record = EmailVerificationToken()
    record.id = uuid.uuid4()
    record.user_id = user.id
    record.token_hash = _hash_token(plaintext)
    record.expires_at = datetime.now(UTC) + expires_in
    record.used_at = datetime.now(UTC) if used else None
    record.created_at = datetime.now(UTC)
    return record, plaintext


def make_db_session_with_results(*results: object) -> MagicMock:
    """Build an :class:`AsyncSession` mock that yields the given values
    on consecutive ``execute().scalar_one_or_none()`` calls.

    Each positional argument is wrapped in a ``MagicMock`` whose
    ``scalar_one_or_none()`` returns that value. ``flush`` is wired as an
    ``AsyncMock`` so service code awaiting it works transparently.
    """
    db = MagicMock()
    db.flush = AsyncMock()

    scalar_results = []
    for value in results:
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = value
        scalar_results.append(result_mock)

    db.execute = AsyncMock(side_effect=scalar_results)
    return db


# ---------------------------------------------------------------------------
# Constants reused across tests
# ---------------------------------------------------------------------------

#: Stable JWT-shaped placeholders so assertions don't depend on real crypto.
VALID_ACCESS_TOKEN = "valid.access.token"
VALID_REFRESH_TOKEN = "valid.refresh.token"
NEW_ACCESS_TOKEN = "new.access.token"
NEW_REFRESH_TOKEN = "new.refresh.token"


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user() -> User:
    """A verified active user — the default for endpoint tests."""
    return make_user()


@pytest.fixture
def unverified_user() -> User:
    """An active but unverified user — for email-verification tests."""
    return make_user(verified=False)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client bound to the FastAPI app.

    Use this instead of constructing ``AsyncClient(transport=...)`` by
    hand in every test. The transport stays in-process (no real network)
    so tests are fast and deterministic.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
