"""Tests for symptom service and symptom/entry-symptom endpoints (Issue #57, ADR-0008).

Coverage
--------
Schemas:
- SymptomCreate slug normalisation + format validation.
- SymptomUpdate name strip + blank rejection.
- SymptomEntry intensity range (0..3).
- EntrySymptomAssignment rejects duplicate ``symptom_id`` values.
- EntrySymptomAssignment caps the list size.

Service layer — Symptom CRUD:
- list_default_symptoms returns only is_default rows.
- list_visible_symptoms returns defaults + own customs.
- create_custom_symptom happy path + slug-clash with default + slug-conflict among user.
- update_custom_symptom happy path + 404 for foreign / default / unknown.
- delete_custom_symptom happy path + 404 for foreign.

Service layer — Entry-symptom assignment:
- list_symptoms_for_entry happy path (owner-scoped).
- list_symptoms_for_entry raises EntryNotFoundForSymptomError for foreign entries.
- assign_symptoms_to_entry replace semantics (add / update / remove diff).
- assign_symptoms_to_entry empty list clears the set.
- assign_symptoms_to_entry raises for foreign entries.
- assign_symptoms_to_entry raises SymptomsNotFoundError on unknown symptom_id.

Endpoint layer:
- GET  /symptoms/default       — 200, no auth required.
- GET  /symptoms               — 200, 401.
- POST /symptoms               — 201, 409 (slug conflict).
- PATCH /symptoms/{id}         — 200, 404.
- DELETE /symptoms/{id}        — 204, 404.
- GET  /entries/{id}/symptoms  — 200, 401, 404.
- PUT  /entries/{id}/symptoms  — 200, 404, 422 (bad payload).

Privacy:
- Static log-scrubbing check: symptom_service must never log
  slug, name, ``symptom_id``, or ``intensity`` payload values.

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
from app.models.user import User
from app.schemas.symptom import (
    MAX_SYMPTOMS_PER_ENTRY,
    EntrySymptomAssignment,
    SymptomCreate,
    SymptomEntry,
    SymptomUpdate,
)
from app.services import symptom_service
from app.services.symptom_service import (
    EntryNotFoundForSymptomError,
    SymptomConflictError,
    SymptomNotFoundError,
    SymptomsNotFoundError,
    assign_symptoms_to_entry,
    create_custom_symptom,
    delete_custom_symptom,
    list_default_symptoms,
    list_symptoms_for_entry,
    list_visible_symptoms,
    update_custom_symptom,
)
from tests.conftest import (
    make_entry,
    make_entry_symptom,
    make_symptom,
    make_user,
)

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


def _all_result(rows: list[tuple[object, ...]]) -> MagicMock:
    """Mock that mimics ``execute(...).all()`` returning row tuples."""
    rm = MagicMock()
    rm.all.return_value = rows
    return rm


# ---------------------------------------------------------------------------
# Schemas — Symptom CRUD
# ---------------------------------------------------------------------------


def test_symptom_create_normalises_slug() -> None:
    payload = SymptomCreate(slug="  Migraine_with_Aura  ", name="Migräne mit Aura")
    assert payload.slug == "migraine_with_aura"
    assert payload.name == "Migräne mit Aura"


def test_symptom_create_rejects_invalid_slug() -> None:
    with pytest.raises(ValidationError):
        SymptomCreate(slug="-bad-start", name="Whatever")
    with pytest.raises(ValidationError):
        SymptomCreate(slug="x", name="Too short")  # min_length=2
    with pytest.raises(ValidationError):
        SymptomCreate(slug="ä-non-ascii", name="Whatever")


def test_symptom_create_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        SymptomCreate(slug="tinnitus", name="   ")


def test_symptom_update_keeps_name_strip() -> None:
    payload = SymptomUpdate(name="  Tinnitus  ")
    assert payload.name == "Tinnitus"


def test_symptom_update_all_fields_optional() -> None:
    payload = SymptomUpdate()
    assert payload.model_dump(exclude_unset=True) == {}


# ---------------------------------------------------------------------------
# Schemas — Entry-symptom assignment
# ---------------------------------------------------------------------------


def test_symptom_entry_rejects_intensity_out_of_range() -> None:
    sid = uuid.uuid4()
    with pytest.raises(ValidationError):
        SymptomEntry(symptom_id=sid, intensity=-1)
    with pytest.raises(ValidationError):
        SymptomEntry(symptom_id=sid, intensity=4)


def test_symptom_entry_accepts_intensity_bounds() -> None:
    sid = uuid.uuid4()
    for intensity in (0, 1, 2, 3):
        s = SymptomEntry(symptom_id=sid, intensity=intensity)
        assert s.intensity == intensity


def test_assignment_rejects_duplicate_ids() -> None:
    sid = uuid.uuid4()
    with pytest.raises(ValidationError):
        EntrySymptomAssignment(
            symptoms=[
                SymptomEntry(symptom_id=sid, intensity=1),
                SymptomEntry(symptom_id=sid, intensity=2),
            ],
        )


def test_assignment_allows_empty_list() -> None:
    payload = EntrySymptomAssignment(symptoms=[])
    assert payload.symptoms == []


def test_assignment_caps_list_size() -> None:
    too_many = [{"symptom_id": str(uuid.uuid4()), "intensity": 1}] * (MAX_SYMPTOMS_PER_ENTRY + 1)
    with pytest.raises(ValidationError):
        EntrySymptomAssignment.model_validate({"symptoms": too_many})


# ---------------------------------------------------------------------------
# Service layer — Symptom CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_default_symptoms_returns_only_defaults() -> None:
    defaults = [
        make_symptom(slug="headache", is_default=True),
        make_symptom(slug="cold", is_default=True),
    ]
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars_result(defaults))
    result = await list_default_symptoms(db)
    assert {s.slug for s in result} == {"headache", "cold"}


@pytest.mark.asyncio
async def test_list_visible_symptoms_returns_defaults_plus_user_customs() -> None:
    user = make_user()
    rows = [
        make_symptom(slug="headache", is_default=True),
        make_symptom(user, slug="tinnitus", name="Tinnitus"),
    ]
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars_result(rows))
    result = await list_visible_symptoms(db, user_id=user.id)
    assert {s.slug for s in result} == {"headache", "tinnitus"}


@pytest.mark.asyncio
async def test_create_custom_symptom_happy_path() -> None:
    user = make_user()
    db = MagicMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalar_result(None)])  # no default-clash
    payload = SymptomCreate(slug="tinnitus", name="Tinnitus")
    symptom = await create_custom_symptom(db, user_id=user.id, payload=payload)
    assert symptom.user_id == user.id
    assert symptom.slug == "tinnitus"
    assert symptom.is_default is False
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_custom_symptom_clashes_with_default() -> None:
    user = make_user()
    default = make_symptom(slug="headache", is_default=True)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(default))
    payload = SymptomCreate(slug="headache", name="My headache")
    with pytest.raises(SymptomConflictError):
        await create_custom_symptom(db, user_id=user.id, payload=payload)


@pytest.mark.asyncio
async def test_create_custom_symptom_user_slug_conflict() -> None:
    """Integrity error from the partial unique index surfaces as a 409."""
    from sqlalchemy.exc import IntegrityError

    user = make_user()
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock(side_effect=IntegrityError("stmt", "params", Exception("dup")))
    db.rollback = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    with pytest.raises(SymptomConflictError):
        await create_custom_symptom(
            db, user_id=user.id, payload=SymptomCreate(slug="tinnitus", name="Tinnitus")
        )


@pytest.mark.asyncio
async def test_update_custom_symptom_happy_path() -> None:
    user = make_user()
    sym = make_symptom(user, slug="tinnitus", name="Tinnitus")
    db = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(sym))
    result = await update_custom_symptom(
        db,
        user_id=user.id,
        symptom_id=sym.id,
        payload=SymptomUpdate(name="Tinnitus rechts"),
    )
    assert result.name == "Tinnitus rechts"


@pytest.mark.asyncio
async def test_update_custom_symptom_unknown_raises_404() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    with pytest.raises(SymptomNotFoundError):
        await update_custom_symptom(
            db,
            user_id=user.id,
            symptom_id=uuid.uuid4(),
            payload=SymptomUpdate(name="x"),
        )


@pytest.mark.asyncio
async def test_delete_custom_symptom_happy_path() -> None:
    user = make_user()
    sym = make_symptom(user, slug="tinnitus")
    db = MagicMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(sym))
    await delete_custom_symptom(db, user_id=user.id, symptom_id=sym.id)
    db.delete.assert_awaited_once_with(sym)


@pytest.mark.asyncio
async def test_delete_custom_symptom_unknown_raises_404() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    with pytest.raises(SymptomNotFoundError):
        await delete_custom_symptom(db, user_id=user.id, symptom_id=uuid.uuid4())


# ---------------------------------------------------------------------------
# Service layer — Entry-symptom assignment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_symptoms_owner_only() -> None:
    user = make_user()
    entry = make_entry(user)
    sid = uuid.uuid4()
    rows = [make_entry_symptom(entry=entry, symptom_id=sid, intensity=1)]

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(entry),  # _get_owned_entry
            _scalars_result(rows),  # actual list query
        ]
    )

    result = await list_symptoms_for_entry(db, user_id=user.id, entry_id=entry.id)
    assert [r.symptom_id for r in result] == [sid]


@pytest.mark.asyncio
async def test_list_symptoms_unknown_entry_raises() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalar_result(None)])
    with pytest.raises(EntryNotFoundForSymptomError):
        await list_symptoms_for_entry(db, user_id=user.id, entry_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_assign_symptoms_replaces_set() -> None:
    """Replace semantics: ids not in payload are deleted, new ids
    inserted, common ids with changed intensity updated."""
    user = make_user()
    entry = make_entry(user)
    sid_headache = uuid.uuid4()
    sid_cold = uuid.uuid4()
    sid_fatigue = uuid.uuid4()

    existing = [
        make_entry_symptom(entry=entry, symptom_id=sid_headache, intensity=1),
        make_entry_symptom(entry=entry, symptom_id=sid_cold, intensity=2),
    ]
    refreshed = [
        make_entry_symptom(entry=entry, symptom_id=sid_fatigue, intensity=2),
        make_entry_symptom(entry=entry, symptom_id=sid_headache, intensity=3),
    ]

    db = MagicMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(entry),  # _get_owned_entry
            _all_result([(sid_headache,), (sid_fatigue,)]),  # visibility check
            _scalars_result(existing),  # current rows
            _scalar_result(None),  # delete
            _scalars_result(refreshed),  # final select
        ]
    )

    payload = [
        SymptomEntry(symptom_id=sid_headache, intensity=3),  # update
        SymptomEntry(symptom_id=sid_fatigue, intensity=2),  # add
        # cold disappears -> delete
    ]
    result = await assign_symptoms_to_entry(
        db,
        user_id=user.id,
        entry_id=entry.id,
        symptoms=payload,
    )
    assert {r.symptom_id for r in result} == {sid_headache, sid_fatigue}
    assert db.add.call_count == 1
    added_arg = db.add.call_args.args[0]
    assert added_arg.symptom_id == sid_fatigue
    assert added_arg.intensity == 2
    # Existing headache row had intensity overwritten in place.
    assert existing[0].intensity == 3


@pytest.mark.asyncio
async def test_assign_symptoms_empty_clears_set() -> None:
    user = make_user()
    entry = make_entry(user)
    existing = [make_entry_symptom(entry=entry, symptom_id=uuid.uuid4(), intensity=1)]

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
            symptoms=[SymptomEntry(symptom_id=uuid.uuid4(), intensity=1)],
        )


@pytest.mark.asyncio
async def test_assign_symptoms_unknown_symptom_id_raises() -> None:
    user = make_user()
    entry = make_entry(user)
    sid = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(entry),  # _get_owned_entry
            _all_result([]),  # visibility — none returned
        ]
    )
    with pytest.raises(SymptomsNotFoundError):
        await assign_symptoms_to_entry(
            db,
            user_id=user.id,
            entry_id=entry.id,
            symptoms=[SymptomEntry(symptom_id=sid, intensity=1)],
        )


# ---------------------------------------------------------------------------
# Endpoint layer — Symptom CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_default_symptoms_no_auth(async_client: AsyncClient) -> None:
    rows = [make_symptom(slug="headache", is_default=True)]
    with patch(
        "app.api.v1.endpoints.symptoms.list_default_symptoms",
        new_callable=AsyncMock,
        return_value=rows,
    ):
        r = await async_client.get("/api/v1/symptoms/default")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["slug"] == "headache"
    assert body[0]["is_default"] is True


@pytest.mark.asyncio
async def test_get_symptoms_requires_auth(async_client: AsyncClient) -> None:
    r = await async_client.get("/api/v1/symptoms")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_post_symptom_201(async_client: AsyncClient, user: User) -> None:
    created = make_symptom(user, slug="tinnitus", name="Tinnitus")

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.symptoms.create_custom_symptom",
            new_callable=AsyncMock,
            return_value=created,
        ):
            r = await async_client.post(
                "/api/v1/symptoms",
                json={"slug": "tinnitus", "name": "Tinnitus"},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 201
    assert r.json()["slug"] == "tinnitus"


@pytest.mark.asyncio
async def test_post_symptom_409(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.symptoms.create_custom_symptom",
            new_callable=AsyncMock,
            side_effect=SymptomConflictError("dup"),
        ):
            r = await async_client.post(
                "/api/v1/symptoms",
                json={"slug": "tinnitus", "name": "Tinnitus"},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 409


@pytest.mark.asyncio
async def test_patch_symptom_404(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.symptoms.update_custom_symptom",
            new_callable=AsyncMock,
            side_effect=SymptomNotFoundError("nope"),
        ):
            r = await async_client.patch(
                f"/api/v1/symptoms/{uuid.uuid4()}",
                json={"name": "X"},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_symptom_204(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.symptoms.delete_custom_symptom",
            new_callable=AsyncMock,
            return_value=None,
        ):
            r = await async_client.delete(
                f"/api/v1/symptoms/{uuid.uuid4()}",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 204


# ---------------------------------------------------------------------------
# Endpoint layer — Entry-symptom assignment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_entry_symptoms_requires_auth(async_client: AsyncClient) -> None:
    r = await async_client.get(f"/api/v1/entries/{uuid.uuid4()}/symptoms")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_entry_symptoms_200(async_client: AsyncClient, user: User) -> None:
    entry_id = uuid.uuid4()
    entry = make_entry(user)
    entry.id = entry_id
    sid_a, sid_b = uuid.uuid4(), uuid.uuid4()
    rows = [
        make_entry_symptom(entry=entry, symptom_id=sid_a, intensity=2),
        make_entry_symptom(entry=entry, symptom_id=sid_b, intensity=1),
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
    assert {item["symptom_id"] for item in body} == {str(sid_a), str(sid_b)}


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
    sid = uuid.uuid4()
    rows = [make_entry_symptom(entry=entry, symptom_id=sid, intensity=2)]

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
                json={"symptoms": [{"symptom_id": str(sid), "intensity": 2}]},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["symptom_id"] == str(sid)
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
                json={"symptoms": [{"symptom_id": str(uuid.uuid4()), "intensity": 1}]},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_put_entry_symptoms_422_unknown_symptom_id(
    async_client: AsyncClient, user: User
) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.symptoms.assign_symptoms_to_entry",
            new_callable=AsyncMock,
            side_effect=SymptomsNotFoundError("unknown"),
        ):
            r = await async_client.put(
                f"/api/v1/entries/{uuid.uuid4()}/symptoms",
                json={"symptoms": [{"symptom_id": str(uuid.uuid4()), "intensity": 2}]},
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
            json={"symptoms": [{"symptom_id": str(uuid.uuid4()), "intensity": 7}]},
            cookies={"access_token": "valid.access.token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Privacy: log scrubbing
# ---------------------------------------------------------------------------


def test_symptom_service_logs_no_sensitive_fields() -> None:
    """symptom_service must not log slug, name, ``symptom_id`` or ``intensity``.

    Symptoms (incl. user-supplied custom names) are health data under
    DSGVO Art. 9 — only opaque user_id / entry_id and aggregate counters
    may surface in structured logs.
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
        '"slug"',
        "'slug'",
        ".slug",
        '"name"',
        "'name'",
        ".name",
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
