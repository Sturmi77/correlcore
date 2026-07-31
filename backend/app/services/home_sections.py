"""Home screen section preferences (#584)."""

from __future__ import annotations

from typing import Literal, TypedDict

HomeSectionKey = Literal[
    "first_week_banner",
    "daily_brief",
    "work_context",
    "weekday_overview",
]

VALID_HOME_SECTION_KEYS: frozenset[str] = frozenset(
    {
        "first_week_banner",
        "daily_brief",
        "work_context",
        "weekday_overview",
    }
)


class HomeSectionPreference(TypedDict):
    key: str
    enabled: bool


DEFAULT_HOME_SECTIONS: list[HomeSectionPreference] = [
    {"key": "first_week_banner", "enabled": True},
    {"key": "daily_brief", "enabled": True},
    {"key": "work_context", "enabled": True},
    {"key": "weekday_overview", "enabled": True},
]


def _coerce_section(raw: object) -> HomeSectionPreference | None:
    if not isinstance(raw, dict):
        return None
    key = raw.get("key")
    enabled = raw.get("enabled")
    if not isinstance(key, str):
        return None
    key = key.strip()
    if key not in VALID_HOME_SECTION_KEYS:
        return None
    if not isinstance(enabled, bool):
        return None
    return {"key": key, "enabled": enabled}


def merge_home_sections(
    stored: list[object] | None,
) -> list[HomeSectionPreference]:
    """Resolve stored preferences with defaults for missing or unknown keys."""
    if not stored:
        return [section.copy() for section in DEFAULT_HOME_SECTIONS]

    merged: list[HomeSectionPreference] = []
    seen: set[str] = set()

    for raw in stored:
        section = _coerce_section(raw)
        if section is None or section["key"] in seen:
            continue
        merged.append(section)
        seen.add(section["key"])

    for default in DEFAULT_HOME_SECTIONS:
        if default["key"] not in seen:
            merged.append(default.copy())
            seen.add(default["key"])

    return merged


def normalize_home_sections(
    sections: list[object] | None,
) -> list[HomeSectionPreference] | None:
    """Validate and dedupe a PATCH payload; empty list is allowed."""
    if sections is None:
        return None

    normalized: list[HomeSectionPreference] = []
    seen: set[str] = set()

    for raw in sections:
        section = _coerce_section(raw)
        if section is None or section["key"] in seen:
            continue
        normalized.append(section)
        seen.add(section["key"])

    return normalized
