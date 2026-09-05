"""Home screen section preferences (#584).

Thin wrapper over the generic section-preference helpers
(``app.services.section_preferences``); Home has no locked sections.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from app.services.section_preferences import (
    SectionPreference,
    merge_sections,
    normalize_sections,
)

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

# Re-exported for backwards compatibility with existing imports.
HomeSectionPreference = SectionPreference


DEFAULT_HOME_SECTIONS: list[SectionPreference] = [
    {"key": "first_week_banner", "enabled": True},
    {"key": "daily_brief", "enabled": True},
    {"key": "work_context", "enabled": True},
    {"key": "weekday_overview", "enabled": True},
]


def merge_home_sections(
    stored: Sequence[object] | None,
) -> list[SectionPreference]:
    """Resolve stored preferences with defaults for missing or unknown keys."""
    return merge_sections(
        stored,
        defaults=DEFAULT_HOME_SECTIONS,
        valid_keys=VALID_HOME_SECTION_KEYS,
    )


def normalize_home_sections(
    sections: Sequence[object] | None,
) -> list[SectionPreference] | None:
    """Validate and dedupe a PATCH payload; empty list is allowed."""
    return normalize_sections(sections, valid_keys=VALID_HOME_SECTION_KEYS)
