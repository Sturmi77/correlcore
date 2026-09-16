"""Unit tests for the marker → tag backfill's pure helpers (#895).

The slug derivation and predefined mapping are pure and covered without a
database. End-to-end backfill behaviour (predefined links, custom-tag creation,
hidden-note exclusion, override preference, cap, idempotency, sync revisions) is
covered by ``test_marker_tag_backfill_integration.py`` against real PostgreSQL.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.crypto import DekUnavailableError
from app.schemas.tag import MAX_TAGS_PER_ENTRY
from app.services import marker_tag_backfill_service as backfill

derive = backfill.derive_custom_tag_slug
PREDEFINED_NOTE_MARKERS = backfill.PREDEFINED_NOTE_MARKERS


@pytest.mark.parametrize(
    ("marker", "expected"),
    [
        ("proben", "proben"),
        ("dog sitting", "dog-sitting"),
        ("work/life", "work-life"),
        ("umzug", "umzug"),
        ("café", "caf"),  # non-ascii stripped, 3 usable chars remain
        ("a-b", "a-b"),
        ("my_thing", "my-thing"),  # underscore normalised to dash
        ("multi   space", "multi-space"),
        ("--edge--", "edge"),
    ],
)
def test_derive_custom_tag_slug_valid(marker: str, expected: str) -> None:
    assert derive(marker) == expected


@pytest.mark.parametrize("marker", ["a", "!", "  ", "-", "é", ""])
def test_derive_custom_tag_slug_unsluggable(marker: str) -> None:
    assert derive(marker) is None


def test_slug_has_no_repeated_separators() -> None:
    assert derive("a  b--c__d") == "a-b-c-d"


def test_slug_truncated_to_64_without_trailing_dash() -> None:
    # A run that would place a dash at position 64 must not leave a trailing dash.
    slug = derive("x" * 63 + " y")
    assert slug is not None
    assert len(slug) <= 64
    assert not slug.endswith("-")
    assert slug == "x" * 63


def test_derived_slugs_satisfy_tagcreate() -> None:
    # Every slug the backfill would derive must pass the strict TagCreate schema.
    from app.models.tag import TagCategory
    from app.schemas.tag import TagCreate

    for marker in ("dog sitting", "work/life", "café", "a-b", "my_thing", "--edge--"):
        slug = derive(marker)
        assert slug is not None
        tag = TagCreate(slug=slug, name=marker[:64], category=TagCategory.OTHER)
        assert tag.slug == slug


def test_mapping_only_covers_unambiguous_predefined() -> None:
    # Generic / overlap predefined markers must not be in the 1:1 tag map.
    assert set(backfill._PREDEFINED_TAG_MAP) == {"conflict", "travel", "achievement"}
    for skipped in ("work", "homeoffice", "social", "movement", "stress", "symptom"):
        assert skipped not in backfill._PREDEFINED_TAG_MAP
        assert skipped in PREDEFINED_NOTE_MARKERS
    # The 1:1 keys are themselves part of the predefined taxonomy.
    assert set(backfill._PREDEFINED_TAG_MAP).issubset(PREDEFINED_NOTE_MARKERS)


def test_cap_constant_reused_from_schema() -> None:
    # The backfill must honour the same per-entry cap the API enforces.
    assert MAX_TAGS_PER_ENTRY == 50


async def test_backfill_isolates_dek_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    # Loading Entry.note_enc without a bound DEK raises DekUnavailableError
    # (CryptoError). That must isolate the user (rollback + continue), not
    # abort siblings mid-loop — the CLI then exits non-zero so 049 does not DROP.
    uid = uuid.uuid4()

    async def _boom(_db: object, *, user_id: uuid.UUID) -> object:
        raise DekUnavailableError("No DEK in request context.")

    async def _one_user(_db: object, *, user_id: uuid.UUID | None) -> list[uuid.UUID]:
        return [uid]

    monkeypatch.setattr(backfill, "_backfill_marker_tags_for_user", _boom)
    monkeypatch.setattr(backfill, "_list_backfill_user_ids", _one_user)

    db = AsyncMock()
    summary = await backfill.backfill_marker_tags(db, commit_per_user=True)
    assert summary.users_failed == 1
    assert summary.users_processed == 0
    db.rollback.assert_awaited()


async def test_cli_exits_nonzero_when_users_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    """049 gates DROP on subprocess exit — users_failed must not return 0."""
    import importlib.util
    from pathlib import Path

    from app.services.marker_tag_backfill_service import MarkerTagBackfillSummary

    script = Path(__file__).resolve().parents[1] / "scripts" / "backfill_marker_tags.py"
    spec = importlib.util.spec_from_file_location("backfill_marker_tags_cli", script)
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    failed = MarkerTagBackfillSummary(users_processed=1, users_failed=2)
    ok = MarkerTagBackfillSummary(users_processed=3, users_failed=0)

    class _SessionCtx:
        async def __aenter__(self) -> AsyncMock:
            return AsyncMock()

        async def __aexit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(cli, "AsyncSessionLocal", lambda: _SessionCtx())
    monkeypatch.setattr(cli, "_parse_args", lambda: type("A", (), {"user_id": None, "dry_run": False})())

    async def _failed(*_a: object, **_k: object) -> MarkerTagBackfillSummary:
        return failed

    async def _ok(*_a: object, **_k: object) -> MarkerTagBackfillSummary:
        return ok

    monkeypatch.setattr(cli, "backfill_marker_tags", _failed)
    assert await cli._main() == 1

    monkeypatch.setattr(cli, "backfill_marker_tags", _ok)
    assert await cli._main() == 0
