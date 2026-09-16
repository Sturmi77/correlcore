"""049 must not rewrite tags; historical backfill mapping stays locked."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from types import ModuleType

from app.data.tag_catalog import DEFAULT_TAGS

_MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations/versions/049_drop_entry_note_markers.py"
)

# Former PREDEFINED_NOTE_MARKERS taxonomy (removed with the marker API).
_PREDEFINED_NOTE_MARKERS = frozenset(
    {
        "work",
        "homeoffice",
        "social",
        "movement",
        "sleep_bad",
        "sleep_good",
        "stress",
        "conflict",
        "symptom",
        "travel",
        "achievement",
    }
)


def _load_049() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_049", _MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _upgrade_source() -> str:
    tree = ast.parse(_MIGRATION.read_text(encoding="utf-8"))
    upgrade = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "upgrade"
    )
    return ast.unparse(upgrade)


def test_049_upgrade_does_not_touch_tags_or_signals() -> None:
    code = _upgrade_source()
    assert "DELETE FROM insights WHERE insight_type = 'note_marker_mood'" in code
    assert "drop_table" in code
    assert "entry_note_markers" in code
    # Comments are stripped by unparse, so these names must not appear as SQL.
    assert "entry_tags" not in code
    assert "entry_note_signals" not in code
    assert "UPDATE " not in code
    assert "INSERT " not in code
    # Do not delete the whole insights table / other insight families.
    assert "DELETE FROM insights;" not in code.replace(" ", "")


def test_049_backfill_mapping_only_covers_note_related_1to1_tags() -> None:
    migration = _load_049()
    converted: frozenset[str] = migration.CONVERTED_PREDEFINED_MARKERS
    skipped: frozenset[str] = migration.SKIPPED_OVERLAP_MARKERS
    catalog = {spec.slug for spec in DEFAULT_TAGS}

    assert converted == frozenset({"conflict", "travel", "achievement"})
    assert converted <= catalog
    # Overlap keys are not catalogue slugs, so they could not silently attach
    # to unrelated defaults such as work_intense / good_sleep / family / sport.
    assert skipped.isdisjoint(catalog)
    assert converted.isdisjoint(skipped)
    assert converted | skipped == _PREDEFINED_NOTE_MARKERS
    # Explicit near-misses that must stay unmapped.
    assert "good_sleep" not in converted
    assert "work_intense" not in converted
    assert "social" not in converted
