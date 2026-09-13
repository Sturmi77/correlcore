"""Unit tests for the custom-marker → tag-slug derivation in migration 048 (#895).

Imports the migration module directly so the pure derivation logic is covered
without a database.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

_MIGRATION = (
    pathlib.Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "048_migrate_note_markers_to_tags.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("m048", _MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m048 = _load()
derive = m048.derive_custom_tag_slug


@pytest.mark.parametrize(
    ("marker", "expected"),
    [
        ("proben", "proben"),
        ("dog sitting", "dog-sitting"),
        ("work/life", "work-life"),
        ("umzug", "umzug"),
        ("café", "caf"),  # non-ascii stripped, 3 usable chars remain
        ("a-b", "a-b"),
        ("multi   space", "multi-space"),  # whitespace already collapsed on write, defensive here
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


def test_slug_truncated_to_64() -> None:
    assert len(derive("x" * 100)) == 64


def test_mapping_only_covers_unambiguous_predefined() -> None:
    # Generic / overlap predefined markers must not be in the 1:1 tag map.
    assert set(m048._PREDEFINED_TAG_MAP) == {"conflict", "travel", "achievement"}
    for skipped in ("work", "homeoffice", "social", "movement", "stress", "symptom"):
        assert skipped not in m048._PREDEFINED_TAG_MAP
        assert skipped in m048._PREDEFINED_MARKERS
