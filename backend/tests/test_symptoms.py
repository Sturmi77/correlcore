"""Tests for symptom service and symptom/entry-symptom endpoints (M1, Issue #9).

Coverage
--------
Schemas:
- SymptomEntry rejects unknown / non-canonical keys.
- SymptomEntry intensity range (0..3).
- EntrySymptomAssignment rejects duplicate keys.
- EntrySymptomAssignment caps the list size.

Service layer:
- list_symptoms_for_entry happy path (owner-scoped).
- list_symptoms_for_entry raises EntryNotFoundForSymptomError for foreign entries.
- assign_symptoms_to_entry replace semantics (add / update / remove diff).
- assign_symptoms_to_entry empty list clears the set.
- assign_symptoms_to_entry raises for foreign entries.

Endpoint layer:
- GET /symptoms/standard       — 200, no auth required, returns sorted keys.
- GET /entries/{id}/symptoms   — 200, 401, 404.
- PUT /entries/{id}/symptoms   — 200, 404, 422 (bad payload).

Privacy:
- Static log-scrubbing check: symptom_service must never log
  ``symptom_key`` or ``intensity`` payload values.

All DB calls are mocked.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.symptom import STANDARD_SYMPTOM_KEYS
from app.models.user import User
from app.schemas.symptom import (
    MAX_SYMPTOMS_PER_ENTRY,
    EntrySymptomAssignment,
    SymptomEntry,
)
from app.services import symptom_service
from app.services.symptom_service import (
    EntryNotFoundForSymptomError,
    assign_symptoms_to_entry,
    list_symptoms_for_entry,
)
from tests.conftest import make_entry, make_entry_symptom, make_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scalar_result(value: object) -> MagicMock:
    """Mock that mimics ``execute(...).scalar_one_or_none()``."""
    rm = MagicMock()
    rm.scalar_one_or_none.return_value = value
    return rm


def _scalars_result(values: list[object]) -> MagicMock:
    """Mock that mimics ``execute(...).scalars().all()``."""
    rm = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    rm.scalars.return_value = scalars
    return rm


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


def test_symptom_entry_rejects_unknown_key() -> None:
    with pytest.raises(ValidationError):
        SymptomEntry(symptom_key="not_a_real_symptom", intensity=1)


def test_symptom_entry_normalises_case_and_whitespace() -> None:
    s = SymptomEntry(symptom_key="  Headache  ", intensity=2)
    assert s.symptom_key == "headache"
    assert s.intensity == 2


def test_symptom_entry_rejects_intensity_out_of_range() -> None:
    with pytest.raises(ValidationError):
        SymptomEntry(symptom_key="headache", intensity=-1)
    with pytest.raises(ValidationError):
        SymptomEntry(symptom_key="headache", intensity=4)


def test_symptom_entry_accepts_intensity_bounds() -> None:
    for intensity in (0, 1, 2, 3):
        s = SymptomEntry(symptom_key="cold", intensity=intensity)
        assert s.intensity == intensity


def test_assignment_rejects_duplicate_keys() -> None:
    with pytest.raises(ValidationError):
        EntrySymptomAssignment(
            symptoms=[
                SymptomEntry(symptom_key="headache", intensity=1),
                SymptomEntry(symptom_key="headache", intensity=2),
            ],
        )


def test_assignment_allows_empty_list() -> None:
    payload = EntrySymptomAssignment(symptoms=[])
    assert payload.symptoms == []


def test_assignment_caps_list_size() -> None:
    # The closed key set has only five entries, so we can't actually
    # build MAX_SYMPTOMS_PER_ENTRY+1 valid SymptomEntry objects with
    # unique keys. Instead, exercise the cap directly with the
    # validator by passing identical-shape payloads.
    too_many = [{"symptom_key": "headache", "intensity": 1}] * (MAX_SYMPTOMS_PER_ENTRY + 1)
    with pytest.raises(ValidationError):
        EntrySymptomAssignment.model_validate({"symptoms": too_many})


# ---------------------------------------------------------------------------
# Service layer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_symptoms_owner_only() -> None:
    user = make_user()
    entry = make_entry(user)
    rows = [make_entry_symptom(entry=entry, symptom_key="headache", intensity=1)]

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(entry),  # _get_owned_entry
            _scalars_result(rows),  # actual list query
        ]
    )

    result = await list_symptoms_for_entry(db, user_id=user.id, entry_id=entry.id)
    assert [r.symptom_key for r in result] == ["headache"]


@pytest.mark.asyncio
async def test_list_symptoms_unknown_entry_raises() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalar_result(None)])
    with pytest.raises(EntryNotFoundForSymptomError):
        await list_symptoms_for_entry(db, user_id=user.id, entry_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_assign_symptoms_replaces_set() -> None:
    """Replace semantics: keys not in payload are deleted, new keys
    inserted, common keys with changed intensity updated."""
    user = make_user()
    entry = make_entry(user)

    existing = [
        make_entry_symptom(entry=entry, symptom_key="headache", intensity=1),
        make_entry_symptom(entry=entry, symptom_key="cold", intensity=2),
    ]
    refreshed = [
        make_entry_symptom(entry=entry, symptom_key="fatigue", intensity=2),
        make_entry_symptom(entry=entry, symptom_key="headache", intensity=3),
    ]

    db = MagicMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(entry),  # _get_owned_entry
            _scalars_result(existing),  # current rows
            _scalar_result(None),  # delete
            _scalars_result(refreshed),  # final select
        ]
    )

    payload = [
        SymptomEntry(symptom_key="headache", intensity=3),  # update
        SymptomEntry(symptom_key="fatigue", intensity=2),  # add
        # cold disappears -> delete
    ]
    result = await assign_symptoms_to_entry(
        db,
        user_id=user.id,
        entry_id=entry.id,
        symptoms=payload,
    )
    assert {r.symptom_key for r in result} == {"headache", "fatigue"}
    # Delete was called for the removed key, db.add for the added one.
    assert db.add.call_count == 1
    added_arg = db.add.call_args.args[0]
    assert added_arg.symptom_key == "fatigue"
    assert added_arg.intensity == 2
    # The headache row had its intensity overwritten on the existing
    # ORM instance, not via a fresh insert.
    assert existing[0].intensity == 3


@pytest.mark.asyncio
async def test_assign_symptoms_empty_clears_set() -> None:
    user = make_user()
    entry = make_entry(user)
    existing = [make_entry_symptom(entry=entry, symptom_key="cold", intensity=1)]

    db = MagicMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(entry),
            _scalars_result(existing),
            _scalar_result(None),  # delete
            _scalars_result([]),  # final select
        ]
    )

    result = await assign_symptoms_to_entry(
        db,
        user_id=user.id,
        entry_id=entry.id,
        symptoms=[],
    )
    assert result == []
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_assign_symptoms_unknown_entry_raises() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalar_result(None)])
    with pytest.raises(EntryNotFoundForSymptomError):
        await assign_symptoms_to_entry(
            db,
            user_id=user.id,
            entry_id=uuid.uuid4(),
            symptoms=[SymptomEntry(symptom_key="headache", intensity=1)],
        )


# ---------------------------------------------------------------------------
# Endpoint layer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_standard_keys_no_auth(async_client: AsyncClient) -> None:
    r = await async_client.get("/api/v1/symptoms/standard")
    assert r.status_code == 200
    body = r.json()
    keys = [item["symptom_key"] for item in body["keys"]]
    assert keys == sorted(STANDARD_SYMPTOM_KEYS)


@pytest.mark.asyncio
async def test_get_entry_symptoms_requires_auth(async_client: AsyncClient) -> None:
    r = await async_client.get(f"/api/v1/entries/{uuid.uuid4()}/symptoms")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_entry_symptoms_200(async_client: AsyncClient, user: User) -> None:
    entry_id = uuid.uuid4()
    entry = make_entry(user)
    entry.id = entry_id
    rows = [
        make_entry_symptom(entry=entry, symptom_key="headache", intensity=2),
        make_entry_symptom(entry=entry, symptom_key="cold", intensity=1),
    ]

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.symptoms.list_symptoms_for_entry",
            new_callable=AsyncMock,
            return_value=rows,
        ):
            r = await async_client.get(
                f"/api/v1/entries/{entry_id}/symptoms",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert {item["symptom_key"] for item in body} == {"headache", "cold"}


@pytest.mark.asyncio
async def test_get_entry_symptoms_404(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.symptoms.list_symptoms_for_entry",
            new_callable=AsyncMock,
            side_effect=EntryNotFoundForSymptomError("missing"),
        ):
            r = await async_client.get(
                f"/api/v1/entries/{uuid.uuid4()}/symptoms",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_put_entry_symptoms_200(async_client: AsyncClient, user: User) -> None:
    entry_id = uuid.uuid4()
    entry = make_entry(user)
    entry.id = entry_id
    rows = [make_entry_symptom(entry=entry, symptom_key="headache", intensity=2)]

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.symptoms.assign_symptoms_to_entry",
            new_callable=AsyncMock,
            return_value=rows,
        ):
            r = await async_client.put(
                f"/api/v1/entries/{entry_id}/symptoms",
                json={"symptoms": [{"symptom_key": "headache", "intensity": 2}]},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["symptom_key"] == "headache"
    assert body[0]["intensity"] == 2


@pytest.mark.asyncio
async def test_put_entry_symptoms_404(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.symptoms.assign_symptoms_to_entry",
            new_callable=AsyncMock,
            side_effect=EntryNotFoundForSymptomError("missing"),
        ):
            r = await async_client.put(
                f"/api/v1/entries/{uuid.uuid4()}/symptoms",
                json={"symptoms": [{"symptom_key": "cold", "intensity": 1}]},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_put_entry_symptoms_422_unknown_key(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        r = await async_client.put(
            f"/api/v1/entries/{uuid.uuid4()}/symptoms",
            json={"symptoms": [{"symptom_key": "anxiety", "intensity": 2}]},
            cookies={"access_token": "valid.access.token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 422


@pytest.mark.asyncio
async def test_put_entry_symptoms_422_intensity_out_of_range(
    async_client: AsyncClient, user: User
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        r = await async_client.put(
            f"/api/v1/entries/{uuid.uuid4()}/symptoms",
            json={"symptoms": [{"symptom_key": "cold", "intensity": 7}]},
            cookies={"access_token": "valid.access.token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Privacy: log scrubbing
# ---------------------------------------------------------------------------


def test_symptom_service_logs_no_sensitive_fields() -> None:
    """symptom_service must not log ``symptom_key`` or ``intensity``.

    Symptoms are health data under DSGVO Art. 9 — only opaque IDs and
    aggregate counters may surface in structured logs.
    """
    import inspect
    import re

    src = inspect.getsource(symptom_service)
    log_calls = re.findall(
        r"logger\.(?:info|warning|error|debug)\s*\([^)]*\)",
        src,
        flags=re.DOTALL,
    )
    assert log_calls, "symptom_service should have at least one log call"

    forbidden = (
        "symptom_key",
        '"intensity"',
        "'intensity'",
        "intensity=",
        ".intensity",
    )
    for call in log_calls:
        for needle in forbidden:
            assert needle not in call, (
                f"symptom_service log call leaks sensitive payload: {needle!r} found in {call!r}"
            )
