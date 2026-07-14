"""Tests for tag service and tag/entry-tag endpoints (M1, Issue #8).

Coverage
--------
Schemas:
- TagCreate slug normalisation + rejection of bad shapes.
- TagCreate color validation.
- EntryTagAssignment uniqueness + cap.

Service layer:
- list_default_tags / list_visible_tags happy paths.
- create_custom_tag — clash with default → 409, IntegrityError → 409.
- update_custom_tag — owner-only for customs, copy-on-write for defaults.
- delete_custom_tag — owner-only.
- assign_tags_to_entry — replace semantics, missing tag → error,
  missing entry → error.

Endpoint layer:
- GET /tags/default      — 200, no auth required.
- GET /tags              — 200, 401 without auth.
- POST /tags             — 201, 409 on conflict, 401 unauth.
- PATCH /tags/{id}       — 200, 404.
- DELETE /tags/{id}      — 204, 404.
- GET /entries/{id}/tags — 200, 404.
- PUT /entries/{id}/tags — 200, 404 entry, 422 unknown tag.

Privacy:
- Static log-scrubbing check for the tag-service module.

All DB calls are mocked.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from app.api.v1.deps.auth import get_current_verified_user
from app.main import app
from app.models.tag import TagCategory
from app.models.user import User
from app.schemas.tag import (
    EntryTagAssignment,
    TagCreate,
    TagUpdate,
)
from app.services import tag_service
from app.services.tag_service import (
    EntryNotFoundForTagError,
    TagConflictError,
    TagNotFoundError,
    TagsNotFoundError,
    TagValidationError,
    active_tag_predicate,
    analytics_tag_predicate,
    assign_tags_to_entry,
    create_custom_tag,
    delete_custom_tag,
    list_default_tags,
    list_tags_for_entry,
    list_visible_tags,
    update_custom_tag,
)
from tests.conftest import make_entry, make_tag, make_user

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
    """Mock that mimics ``execute(...).all()`` (used for ``select(Col)``)."""
    rm = MagicMock()
    rm.all.return_value = rows
    return rm


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


def test_tag_create_lowercases_slug() -> None:
    payload = TagCreate(
        slug="  Meditation  ",
        name="Meditation",
        category=TagCategory.HEALTH,
    )
    assert payload.slug == "meditation"


def test_tag_create_rejects_invalid_slug() -> None:
    with pytest.raises(ValueError):
        TagCreate(
            slug="-bad-",
            name="Bad",
            category=TagCategory.OTHER,
        )


def test_tag_create_validates_color() -> None:
    with pytest.raises(ValueError):
        TagCreate(
            slug="ok",
            name="Ok",
            category=TagCategory.OTHER,
            color="not-a-color",
        )
    payload = TagCreate(
        slug="ok",
        name="Ok",
        category=TagCategory.OTHER,
        color="#AABBCC",
    )
    assert payload.color == "#aabbcc"


def test_tag_create_validates_habit_fields() -> None:
    payload = TagCreate(
        slug="walk",
        name="Walk",
        category=TagCategory.SPORT,
        habit_type="build",
        target_frequency=4,
    )
    assert payload.habit_type == "build"
    assert payload.target_frequency == 4

    with pytest.raises(ValueError):
        TagCreate(
            slug="sleep",
            name="Sleep",
            category=TagCategory.HEALTH,
            habit_type="reduce",
        )


def test_tag_update_clears_target_frequency_for_non_habit() -> None:
    payload = TagUpdate(habit_type="none", target_frequency=4)
    assert payload.target_frequency is None


def test_tag_update_allows_partial_habit_type_patch() -> None:
    payload = TagUpdate(habit_type="build")
    assert payload.habit_type == "build"
    assert payload.target_frequency is None


def test_entry_tag_assignment_rejects_duplicates() -> None:
    tid = uuid.uuid4()
    with pytest.raises(ValueError):
        EntryTagAssignment(tag_ids=[tid, tid])


# ---------------------------------------------------------------------------
# Service: list_default_tags / list_visible_tags
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_default_tags_returns_only_defaults() -> None:
    defaults = [make_tag(slug=f"d{i}", is_default=True) for i in range(3)]
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars_result(defaults))

    out = await list_default_tags(db)
    assert out == defaults


@pytest.mark.asyncio
async def test_list_visible_tags_clamps_limit() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars_result([]))

    out = await list_visible_tags(db, user_id=user.id, limit=10_000)
    assert out == []
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_visible_tags_filters_hidden_by_default() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars_result([]))

    await list_visible_tags(db, user_id=user.id)

    stmt = db.execute.await_args.args[0]
    assert "tags.is_hidden IS false" in str(stmt.whereclause)


@pytest.mark.asyncio
async def test_list_visible_tags_can_include_hidden() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars_result([]))

    await list_visible_tags(db, user_id=user.id, include_hidden=True)

    stmt = db.execute.await_args.args[0]
    assert "tags.is_hidden IS false" not in str(stmt.whereclause)


def test_active_tag_predicate_respects_hidden_default_overrides() -> None:
    user = make_user()

    predicate = active_tag_predicate(user.id)

    text = str(predicate)
    assert "tags.is_hidden IS false" in text
    assert "EXISTS" in text
    assert "is_hidden IS true" in text


def test_analytics_tag_predicate_requires_include_in_analytics() -> None:
    user = make_user()

    predicate = analytics_tag_predicate(user.id)

    text = str(predicate)
    assert "tags.is_hidden IS false" in text
    assert "include_in_analytics IS true" in text
    assert "include_in_analytics IS false" in text
    assert "EXISTS" in text


@pytest.mark.asyncio
async def test_update_custom_tag_can_exclude_from_analytics() -> None:
    user = make_user()
    tag = make_tag(user, slug="medication", name="Medication", include_in_analytics=True)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(tag))
    db.flush = AsyncMock()

    out = await update_custom_tag(
        db,
        user_id=user.id,
        tag_id=tag.id,
        payload=TagUpdate(include_in_analytics=False),
    )

    assert out.include_in_analytics is False
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_default_tag_copies_include_in_analytics_into_override() -> None:
    user = make_user()
    default = make_tag(slug="sport", name="Sport", is_default=True, include_in_analytics=True)
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(default),
            _scalar_result(None),
        ]
    )
    db.add = MagicMock()
    db.flush = AsyncMock()

    out = await update_custom_tag(
        db,
        user_id=user.id,
        tag_id=default.id,
        payload=TagUpdate(include_in_analytics=False),
    )

    assert out.include_in_analytics is False
    assert out.is_default is False
    assert out.user_id == user.id
    db.add.assert_called_once()


# ---------------------------------------------------------------------------
# Service: create_custom_tag
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_custom_tag_happy_path() -> None:
    user = make_user()
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    # First execute: default-clash check returns nothing.
    db.execute = AsyncMock(return_value=_scalar_result(None))

    tag = await create_custom_tag(
        db,
        user_id=user.id,
        payload=TagCreate(slug="custom", name="Custom", category=TagCategory.OTHER),
    )

    assert tag.user_id == user.id
    assert tag.slug == "custom"
    assert tag.is_default is False
    assert tag.habit_type == "none"
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_custom_tag_clashes_with_default() -> None:
    user = make_user()
    existing_default = make_tag(slug="sport", is_default=True)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(existing_default))

    with pytest.raises(TagConflictError):
        await create_custom_tag(
            db,
            user_id=user.id,
            payload=TagCreate(slug="sport", name="My Sport", category=TagCategory.SPORT),
        )


@pytest.mark.asyncio
async def test_create_custom_tag_duplicate_slug_raises_conflict() -> None:
    """IntegrityError on flush → TagConflictError + rollback."""
    user = make_user()
    integrity = IntegrityError("INSERT", params=None, orig=Exception("uq"))
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock(side_effect=integrity)
    db.rollback = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(None))

    with pytest.raises(TagConflictError):
        await create_custom_tag(
            db,
            user_id=user.id,
            payload=TagCreate(slug="custom", name="Custom", category=TagCategory.OTHER),
        )

    db.rollback.assert_awaited_once()


# ---------------------------------------------------------------------------
# Service: update_custom_tag / delete_custom_tag
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_custom_tag_owner_only() -> None:
    user = make_user()
    tag = make_tag(user, slug="x", name="X")
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(tag))
    db.flush = AsyncMock()

    out = await update_custom_tag(
        db,
        user_id=user.id,
        tag_id=tag.id,
        payload=TagUpdate(name="Renamed", color="#112233"),
    )

    assert out.name == "Renamed"
    assert out.color == "#112233"


@pytest.mark.asyncio
async def test_update_custom_tag_not_found_for_default_or_foreign() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    db.flush = AsyncMock()

    with pytest.raises(TagNotFoundError):
        await update_custom_tag(
            db,
            user_id=user.id,
            tag_id=uuid.uuid4(),
            payload=TagUpdate(name="x"),
        )


@pytest.mark.asyncio
async def test_update_default_tag_creates_user_override() -> None:
    user = make_user()
    default = make_tag(
        slug="sport",
        name="Sport",
        is_default=True,
        habit_type="build",
        target_frequency=3,
    )
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(default),
            _scalar_result(None),
        ]
    )

    out = await update_custom_tag(
        db,
        user_id=user.id,
        tag_id=default.id,
        payload=TagUpdate(name="Training", color="#112233"),
    )

    assert out is not default
    assert out.user_id == user.id
    assert out.slug == default.slug
    assert out.name == "Training"
    assert out.color == "#112233"
    assert out.is_default is False
    assert out.habit_type == "build"
    assert out.target_frequency == 3
    assert default.name == "Sport"
    db.add.assert_called_once_with(out)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_default_tag_partial_habit_patch_uses_existing_target() -> None:
    user = make_user()
    default = make_tag(
        slug="sport",
        name="Sport",
        is_default=True,
        habit_type="build",
        target_frequency=3,
    )
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(default),
            _scalar_result(None),
        ]
    )

    out = await update_custom_tag(
        db,
        user_id=user.id,
        tag_id=default.id,
        payload=TagUpdate(habit_type="reduce"),
    )

    assert out.habit_type == "reduce"
    assert out.target_frequency == 3
    db.add.assert_called_once_with(out)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_tag_rejects_habit_without_effective_target() -> None:
    user = make_user()
    tag = make_tag(user, slug="custom", habit_type="none", target_frequency=None)
    db = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(tag))

    with pytest.raises(TagValidationError):
        await update_custom_tag(
            db,
            user_id=user.id,
            tag_id=tag.id,
            payload=TagUpdate(habit_type="build"),
        )

    db.flush.assert_not_called()


@pytest.mark.asyncio
async def test_update_default_tag_reuses_existing_user_override() -> None:
    user = make_user()
    default = make_tag(slug="sport", name="Sport", is_default=True)
    override = make_tag(user, slug="sport", name="My Sport")
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(default),
            _scalar_result(override),
        ]
    )

    out = await update_custom_tag(
        db,
        user_id=user.id,
        tag_id=default.id,
        payload=TagUpdate(is_hidden=True),
    )

    assert out is override
    assert out.is_hidden is True
    db.add.assert_not_called()
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_custom_tag_calls_db_delete() -> None:
    user = make_user()
    tag = make_tag(user, slug="x", name="X")
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(tag))
    db.delete = AsyncMock()
    db.flush = AsyncMock()

    await delete_custom_tag(db, user_id=user.id, tag_id=tag.id)

    db.delete.assert_awaited_once_with(tag)
    db.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# Service: assign_tags_to_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_tags_replaces_set() -> None:
    """Replace semantics: missing tags get removed, new tags inserted."""
    user = make_user()
    entry = make_entry(user)
    keep = uuid.uuid4()
    add = uuid.uuid4()
    drop = uuid.uuid4()

    # Sequence of execute() returns (in service-call order):
    #  1. _get_owned_entry → entry
    #  2. visibility check  → list of (id,) rows for {keep, add}
    #  3. current set       → list of (id,) rows for {keep, drop}
    #  4. delete            → MagicMock (rowcount unused)
    #  5. final select      → scalars().all() with the new tags
    new_tags = [
        make_tag(user, slug="keep"),
        make_tag(user, slug="add"),
    ]
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(entry),
            _all_result([(keep,), (add,)]),
            _all_result([(keep,), (drop,)]),
            MagicMock(),  # delete
            _scalars_result(new_tags),
        ]
    )

    out = await assign_tags_to_entry(
        db,
        user_id=user.id,
        entry_id=entry.id,
        tag_ids=[keep, add],
    )

    assert out == new_tags
    # 5 execute calls in total
    assert db.execute.await_count == 5
    # Exactly one EntryTag added (for `add`); `keep` is unchanged.
    assert db.add.call_count == 1


@pytest.mark.asyncio
async def test_assign_tags_unknown_tag_raises() -> None:
    user = make_user()
    entry = make_entry(user)
    requested = uuid.uuid4()

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(entry),
            _all_result([]),  # nothing visible
        ]
    )

    with pytest.raises(TagsNotFoundError):
        await assign_tags_to_entry(
            db,
            user_id=user.id,
            entry_id=entry.id,
            tag_ids=[requested],
        )


@pytest.mark.asyncio
async def test_assign_tags_unknown_entry_raises() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(None))

    with pytest.raises(EntryNotFoundForTagError):
        await assign_tags_to_entry(
            db,
            user_id=user.id,
            entry_id=uuid.uuid4(),
            tag_ids=[uuid.uuid4()],
        )


@pytest.mark.asyncio
async def test_assign_empty_list_clears_set() -> None:
    """Empty target → drop everything, return []."""
    user = make_user()
    entry = make_entry(user)
    drop = uuid.uuid4()

    db = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(entry),
            # No visibility check when target is empty.
            _all_result([(drop,)]),  # current set
            MagicMock(),  # delete
        ]
    )

    out = await assign_tags_to_entry(
        db,
        user_id=user.id,
        entry_id=entry.id,
        tag_ids=[],
    )

    assert out == []


# ---------------------------------------------------------------------------
# Service: list_tags_for_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tags_for_entry_owner_only() -> None:
    user = make_user()
    entry = make_entry(user)
    tags = [make_tag(user, slug=f"t{i}") for i in range(2)]

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar_result(entry),
            _scalars_result(tags),
        ]
    )

    out = await list_tags_for_entry(db, user_id=user.id, entry_id=entry.id)
    assert out == tags


@pytest.mark.asyncio
async def test_list_tags_for_entry_unknown_entry() -> None:
    user = make_user()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(None))

    with pytest.raises(EntryNotFoundForTagError):
        await list_tags_for_entry(db, user_id=user.id, entry_id=uuid.uuid4())


# ---------------------------------------------------------------------------
# Endpoint layer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_default_tags_no_auth(async_client: AsyncClient) -> None:
    defaults = [make_tag(slug=f"d{i}", is_default=True) for i in range(2)]
    with patch(
        "app.api.v1.endpoints.tags.list_default_tags",
        new_callable=AsyncMock,
        return_value=defaults,
    ):
        r = await async_client.get("/api/v1/tags/default")

    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert all(item["is_default"] for item in body)


@pytest.mark.asyncio
async def test_get_tags_requires_auth(async_client: AsyncClient) -> None:
    r = await async_client.get("/api/v1/tags")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_tags_200(async_client: AsyncClient, user: User) -> None:
    rows = [make_tag(slug="a", is_default=True), make_tag(user, slug="b")]

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.tags.list_visible_tags",
            new_callable=AsyncMock,
            return_value=rows,
        ):
            r = await async_client.get(
                "/api/v1/tags?include_hidden=true",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["is_hidden"] is False


@pytest.mark.asyncio
async def test_post_tag_201(async_client: AsyncClient, user: User) -> None:
    new_tag = make_tag(user, slug="custom", name="Custom")

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.tags.create_custom_tag",
            new_callable=AsyncMock,
            return_value=new_tag,
        ):
            r = await async_client.post(
                "/api/v1/tags",
                json={"slug": "custom", "name": "Custom", "category": "other"},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 201
    body = r.json()
    assert body["slug"] == "custom"
    assert body["is_default"] is False


@pytest.mark.asyncio
async def test_post_tag_conflict_409(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.tags.create_custom_tag",
            new_callable=AsyncMock,
            side_effect=TagConflictError("dupe"),
        ):
            r = await async_client.post(
                "/api/v1/tags",
                json={"slug": "custom", "name": "Custom", "category": "other"},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 409


@pytest.mark.asyncio
async def test_patch_tag_200(async_client: AsyncClient, user: User) -> None:
    updated = make_tag(
        user,
        slug="custom",
        name="Renamed",
        habit_type="build",
        target_frequency=4,
    )

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.tags.update_custom_tag",
            new_callable=AsyncMock,
            return_value=updated,
        ):
            r = await async_client.patch(
                f"/api/v1/tags/{updated.id}",
                json={"name": "Renamed", "habit_type": "build", "target_frequency": 4},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"
    assert r.json()["habit_type"] == "build"
    assert r.json()["target_frequency"] == 4


@pytest.mark.asyncio
async def test_patch_tag_404(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.tags.update_custom_tag",
            new_callable=AsyncMock,
            side_effect=TagNotFoundError("missing"),
        ):
            r = await async_client.patch(
                f"/api/v1/tags/{uuid.uuid4()}",
                json={"name": "x"},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_tag_204(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.tags.delete_custom_tag",
            new_callable=AsyncMock,
            return_value=None,
        ):
            r = await async_client.delete(
                f"/api/v1/tags/{uuid.uuid4()}",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_tag_404(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.tags.delete_custom_tag",
            new_callable=AsyncMock,
            side_effect=TagNotFoundError("missing"),
        ):
            r = await async_client.delete(
                f"/api/v1/tags/{uuid.uuid4()}",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_entry_tags_200(async_client: AsyncClient, user: User) -> None:
    entry_id = uuid.uuid4()
    tags = [make_tag(user, slug=f"t{i}") for i in range(2)]

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.tags.list_tags_for_entry",
            new_callable=AsyncMock,
            return_value=tags,
        ):
            r = await async_client.get(
                f"/api/v1/entries/{entry_id}/tags",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_get_entry_tags_404(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.tags.list_tags_for_entry",
            new_callable=AsyncMock,
            side_effect=EntryNotFoundForTagError("missing"),
        ):
            r = await async_client.get(
                f"/api/v1/entries/{uuid.uuid4()}/tags",
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_put_entry_tags_200(async_client: AsyncClient, user: User) -> None:
    entry_id = uuid.uuid4()
    tag = make_tag(user, slug="x")

    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.tags.assign_tags_to_entry",
            new_callable=AsyncMock,
            return_value=[tag],
        ):
            r = await async_client.put(
                f"/api/v1/entries/{entry_id}/tags",
                json={"tag_ids": [str(tag.id)]},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["slug"] == "x"


@pytest.mark.asyncio
async def test_put_entry_tags_unknown_tag_422(async_client: AsyncClient, user: User) -> None:
    async def override() -> User:
        return user

    app.dependency_overrides[get_current_verified_user] = override
    try:
        with patch(
            "app.api.v1.endpoints.tags.assign_tags_to_entry",
            new_callable=AsyncMock,
            side_effect=TagsNotFoundError("nope"),
        ):
            r = await async_client.put(
                f"/api/v1/entries/{uuid.uuid4()}/tags",
                json={"tag_ids": [str(uuid.uuid4())]},
                cookies={"access_token": "valid.access.token"},
            )
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Privacy: log scrubbing
# ---------------------------------------------------------------------------


def test_tag_service_logs_no_sensitive_fields() -> None:
    """Tag service must not log slug, name, or tag IDs as user data.

    ``tag_id`` *is* in some log calls (it's an opaque UUID, not user
    data), but slug/name carry behavioural meaning when correlated and
    must stay out of logs.
    """
    import inspect
    import re

    src = inspect.getsource(tag_service)
    log_calls = re.findall(
        r"logger\.(?:info|warning|error|debug)\s*\([^)]*\)",
        src,
        flags=re.DOTALL,
    )
    assert log_calls, "tag_service should have at least one log call"

    forbidden = ("slug", "tag.name", '"name"', "name=")
    for call in log_calls:
        for needle in forbidden:
            assert needle not in call, f"sensitive field {needle!r} leaked: {call}"
