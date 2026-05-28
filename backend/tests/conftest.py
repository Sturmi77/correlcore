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

import base64
import os
import secrets
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Unit tests must not require external Redis just because endpoint-level rate
# limits are enabled in production. Set this before importing app.main, where
# the process-wide SlowAPI limiter is created.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("RATE_LIMIT_STORAGE_URL", "memory://")
os.environ.setdefault(
    "SECRET_KEY",
    "test-" + "-".join(["secret", "key", "for", "correlcore", "checks"]),
)
os.environ.setdefault(
    "ENCRYPTION_KEY",
    base64.urlsafe_b64encode(b"0" * 32).decode(),
)

from app.core.crypto import (
    encrypt_with_dek,
    generate_dek,
    reset_current_user_dek,
    set_current_user_dek,
)
from app.main import app
from app.models.email_verification_token import EmailVerificationToken
from app.models.entry import Entry, EntrySlot, EntrySource, WorkContext
from app.models.symptom import EntrySymptom, Symptom
from app.models.tag import EntryTag, Tag, TagCategory
from app.models.user import User
from app.services.auth_service import _hash_token

# ---------------------------------------------------------------------------
# Issue #26 — module-scope DEK for tests
# ---------------------------------------------------------------------------
# All tests run with one synthetic DEK bound globally. Endpoint tests that
# override ``get_current_verified_user`` bypass the real auth dependency and
# therefore also bypass the DEK-binding step — the autouse fixture below
# closes that gap so encrypted-field access (``Symptom.display_name``,
# ``EncryptedString`` round-trips) keeps working in tests.

_TEST_DEK = generate_dek()

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


def make_entry(
    user: User,
    *,
    entry_date: date | None = None,
    slot: EntrySlot = EntrySlot.DAY,
    mood_score: int = 3,
    energy: int = 3,
    stress: int = 3,
    cycle_day: int | None = None,
    source: EntrySource = EntrySource.DIRECT,
    work_context: WorkContext = WorkContext.HOMEOFFICE,
    note: str | None = None,
) -> Entry:
    """Build a detached :class:`Entry` for service-layer tests.

    Defaults to today's date and a neutral 3/3/3 mood — call sites only
    override what they actually exercise.
    """
    e = Entry()
    e.id = uuid.uuid4()
    e.user_id = user.id
    e.entry_date = entry_date or date.today()
    e.slot = slot
    e.mood_score = mood_score
    e.energy = energy
    e.stress = stress
    e.cycle_day = cycle_day
    e.source = source
    e.work_context = work_context
    # Issue #26: ``note`` on the model maps to ``note_enc`` storage. In
    # tests we set the plaintext directly because the service tests use
    # MagicMock sessions that never trigger the ``EncryptedString``
    # TypeDecorator. The endpoint tests rely on the auto-bound DEK below.
    e.note_enc = note  # type: ignore[assignment]
    e.created_at = datetime.now(UTC)
    e.updated_at = datetime.now(UTC)
    return e


def make_tag(
    user: User | None = None,
    *,
    slug: str = "sport",
    name: str = "Sport",
    category: TagCategory = TagCategory.SPORT,
    icon: str | None = "dumbbell",
    color: str | None = "#10b981",
    is_default: bool = False,
    is_hidden: bool = False,
    habit_type: str = "none",
    target_frequency: int | None = None,
) -> Tag:
    """Build a detached :class:`Tag` for service-layer tests.

    Pass ``user=None`` together with ``is_default=True`` to model a
    curated default tag. Otherwise the tag is owned by ``user``.
    """
    t = Tag()
    t.id = uuid.uuid4()
    t.user_id = None if is_default else (user.id if user is not None else uuid.uuid4())
    t.slug = slug
    t.name = name
    t.category = category
    t.icon = icon
    t.color = color
    t.is_default = is_default
    t.is_hidden = is_hidden
    t.habit_type = habit_type
    t.target_frequency = target_frequency
    t.created_at = datetime.now(UTC)
    t.updated_at = datetime.now(UTC)
    return t


def make_entry_tag(
    *,
    entry: Entry,
    tag: Tag,
) -> EntryTag:
    """Build a detached :class:`EntryTag` link row."""
    et = EntryTag()
    et.entry_id = entry.id
    et.tag_id = tag.id
    et.user_id = entry.user_id
    et.created_at = datetime.now(UTC)
    return et


def make_symptom(
    user: User | None = None,
    *,
    slug: str = "headache",
    name: str = "Kopfschmerzen",
    icon: str | None = "\U0001f915",
    is_default: bool = False,
    symptom_id: uuid.UUID | None = None,
) -> Symptom:
    """Build a detached :class:`Symptom` for service-layer tests.

    Pass ``user=None`` together with ``is_default=True`` to model a
    curated default symptom. Otherwise the symptom is owned by ``user``.
    """
    s = Symptom()
    s.id = symptom_id or uuid.uuid4()
    s.user_id = None if is_default else (user.id if user is not None else uuid.uuid4())
    s.slug = slug
    s.icon = icon
    s.is_default = is_default
    # Issue #26: defaults keep ``name`` plaintext; custom symptoms store
    # the Fernet ciphertext in ``name_enc`` and leave ``name`` NULL. The
    # encrypt path uses the module-scope test DEK so the ContextVar does
    # not need to be bound at construction time.
    if is_default:
        s.name = name
    else:
        s.name = None
        s.name_enc = encrypt_with_dek(name, _TEST_DEK)
    s.created_at = datetime.now(UTC)
    s.updated_at = datetime.now(UTC)
    return s


def make_entry_symptom(
    *,
    entry: Entry,
    symptom: Symptom | None = None,
    symptom_id: uuid.UUID | None = None,
    intensity: int = 1,
) -> EntrySymptom:
    """Build a detached :class:`EntrySymptom` row for service-layer tests."""
    es = EntrySymptom()
    es.id = uuid.uuid4()
    es.entry_id = entry.id
    es.user_id = entry.user_id
    es.symptom_id = (
        symptom_id
        if symptom_id is not None
        else (symptom.id if symptom is not None else uuid.uuid4())
    )
    es.intensity = intensity
    es.created_at = datetime.now(UTC)
    es.updated_at = datetime.now(UTC)
    return es


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


@pytest.fixture(autouse=True)
def _bind_test_dek() -> Generator[None, None, None]:
    """Bind the synthetic test DEK for every test (Issue #26).

    The DEK is normally bound by ``get_current_user`` during request
    handling. Tests override that dependency, so we bind a stable
    module-scope DEK here. Tests that care about the unauthenticated
    path (e.g. ``GET /symptoms/default``) still work because the default
    code paths only read plaintext ``Symptom.name`` and never touch the
    ContextVar.
    """
    token = set_current_user_dek(uuid.uuid4(), _TEST_DEK)
    try:
        yield
    finally:
        reset_current_user_dek(token)


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
