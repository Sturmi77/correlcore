"""Contract checks for backend schema values mirrored in the web client."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from app.models.entry import EntrySlot, EntrySource, WorkContext
from app.schemas.entry import BACKDATE_DAYS_LIMIT, MAX_NOTE_LENGTH, EntryCreate, EntryUpdate

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_CONTRACT = REPO_ROOT / "apps" / "web" / "src" / "lib" / "contracts" / "apiContract.ts"


def _contract_array(name: str) -> list[str]:
    text = FRONTEND_CONTRACT.read_text(encoding="utf-8")
    match = re.search(rf"{name}:\s*(\[[^\]]+\])", text)
    assert match is not None, f"{name} missing from frontend API contract"
    return ast.literal_eval(match.group(1))


def _contract_metric_range(name: str) -> tuple[int, int]:
    text = FRONTEND_CONTRACT.read_text(encoding="utf-8")
    match = re.search(rf"{name}:\s*\{{\s*min:\s*(\d+),\s*max:\s*(\d+),", text)
    assert match is not None, f"{name} metric range missing from frontend API contract"
    return int(match.group(1)), int(match.group(2))


def _schema_range(
    schema: type[EntryCreate] | type[EntryUpdate], field_name: str
) -> tuple[int, int]:
    field_schema = schema.model_json_schema()["properties"][field_name]
    constrained_schema = next(
        (item for item in field_schema.get("anyOf", []) if "minimum" in item),
        field_schema,
    )
    return int(constrained_schema["minimum"]), int(constrained_schema["maximum"])


def test_frontend_entry_enums_match_backend_models() -> None:
    assert _contract_array("entrySlots") == [item.value for item in EntrySlot]
    assert _contract_array("entrySources") == [item.value for item in EntrySource]
    assert _contract_array("workContexts") == [item.value for item in WorkContext]


def test_frontend_entry_metric_ranges_match_backend_schema() -> None:
    for field_name in ("mood_score", "energy", "stress"):
        assert _contract_metric_range(field_name) == (1, 5)
        assert _schema_range(EntryCreate, field_name) == _contract_metric_range(field_name)
        assert _schema_range(EntryUpdate, field_name) == _contract_metric_range(field_name)


def test_frontend_entry_limits_match_backend_schema_constants() -> None:
    text = FRONTEND_CONTRACT.read_text(encoding="utf-8")
    assert f"noteMaxLength: {MAX_NOTE_LENGTH}" in text
    assert f"backdateDaysLimit: {BACKDATE_DAYS_LIMIT}" in text
