"""Generic configurable-section preferences (#821).

Shared merge/normalize/coerce logic behind both the Home screen sections
(#584) and the Insights page sections (#821). Each caller supplies its own
valid-key whitelist, default order, and optional locked keys (sections that
must always stay enabled, e.g. the Insights main feed).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TypedDict


class SectionPreference(TypedDict):
    key: str
    enabled: bool


def _coerce_section(
    raw: object,
    valid_keys: frozenset[str],
    locked_keys: frozenset[str],
) -> SectionPreference | None:
    if not isinstance(raw, dict):
        return None
    key = raw.get("key")
    enabled = raw.get("enabled")
    if not isinstance(key, str):
        return None
    key = key.strip()
    if key not in valid_keys:
        return None
    if not isinstance(enabled, bool):
        return None
    if key in locked_keys:
        enabled = True
    return {"key": key, "enabled": enabled}


def merge_sections(
    stored: Sequence[object] | None,
    *,
    defaults: Sequence[SectionPreference],
    valid_keys: frozenset[str],
    locked_keys: frozenset[str] = frozenset(),
) -> list[SectionPreference]:
    """Resolve stored preferences with defaults for missing or unknown keys."""
    if not stored:
        return [section.copy() for section in defaults]

    merged: list[SectionPreference] = []
    seen: set[str] = set()

    for raw in stored:
        section = _coerce_section(raw, valid_keys, locked_keys)
        if section is None or section["key"] in seen:
            continue
        merged.append(section)
        seen.add(section["key"])

    for default in defaults:
        if default["key"] not in seen:
            merged.append(default.copy())
            seen.add(default["key"])

    return merged


def normalize_sections(
    sections: Sequence[object] | None,
    *,
    valid_keys: frozenset[str],
    locked_keys: frozenset[str] = frozenset(),
) -> list[SectionPreference] | None:
    """Validate and dedupe a PATCH payload; empty list is allowed."""
    if sections is None:
        return None

    normalized: list[SectionPreference] = []
    seen: set[str] = set()

    for raw in sections:
        section = _coerce_section(raw, valid_keys, locked_keys)
        if section is None or section["key"] in seen:
            continue
        normalized.append(section)
        seen.add(section["key"])

    return normalized


def frozen_keys(keys: Iterable[str]) -> frozenset[str]:
    return frozenset(keys)
