"""Insights page section preferences (#821) + Phase 6 versioned hub shrink (D5).

Configurable order and visibility for the ``/insights`` page blocks, mirroring
the Home screen mechanism (#584). The main insight feed (``insight_feed``) is a
locked section: always enabled (never hidden), but freely reorderable.

Phase 6 introduces ``CURRENT_INSIGHT_SECTIONS_VERSION`` so a one-time migrate
can shrink the Layer-1 default without wiping conscious Settings choices.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from app.services.section_preferences import (
    SectionPreference,
    merge_sections,
    normalize_sections,
)

InsightSectionKey = Literal[
    "stage_header",
    "correlation_matrix",
    "insight_feed",
    "lag_heatmap",
    "dismissed",
    "symptom_analytics",
    "tag_groups",
    "tag_cooccurrence",
]

VALID_INSIGHT_SECTION_KEYS: frozenset[str] = frozenset(
    {
        "stage_header",
        "correlation_matrix",
        "insight_feed",
        "lag_heatmap",
        "dismissed",
        "symptom_analytics",
        "tag_groups",
        "tag_cooccurrence",
    }
)

# The main feed cannot be hidden — only reordered.
LOCKED_INSIGHT_SECTION_KEYS: frozenset[str] = frozenset({"insight_feed"})

InsightSectionPreference = SectionPreference

# Pre-Phase-6 default (all on). Used only to detect "saved defaults" layouts.
LEGACY_DEFAULT_INSIGHT_SECTIONS: list[SectionPreference] = [
    {"key": "stage_header", "enabled": True},
    {"key": "correlation_matrix", "enabled": True},
    {"key": "insight_feed", "enabled": True},
    {"key": "lag_heatmap", "enabled": True},
    {"key": "dismissed", "enabled": True},
    {"key": "symptom_analytics", "enabled": True},
    {"key": "tag_groups", "enabled": True},
    {"key": "tag_cooccurrence", "enabled": True},
]

# Phase 6 / D5: slim Layer-1 entry. Optional blocks stay valid for Settings.
DEFAULT_INSIGHT_SECTIONS: list[SectionPreference] = [
    {"key": "stage_header", "enabled": True},
    {"key": "insight_feed", "enabled": True},
    {"key": "correlation_matrix", "enabled": False},
    {"key": "lag_heatmap", "enabled": False},
    {"key": "dismissed", "enabled": False},
    {"key": "symptom_analytics", "enabled": False},
    {"key": "tag_groups", "enabled": False},
    {"key": "tag_cooccurrence", "enabled": False},
]

# Keys that leave the default viewport in v2 (still in validKeys).
SHRINK_INSIGHT_SECTION_KEYS: frozenset[str] = frozenset(
    {
        "correlation_matrix",
        "lag_heatmap",
        "dismissed",
        "symptom_analytics",
        "tag_groups",
        "tag_cooccurrence",
    }
)

# Version 1 = legacy all-on layout era; version 2 = slim hub defaults.
CURRENT_INSIGHT_SECTIONS_VERSION = 2
LEGACY_INSIGHT_SECTIONS_VERSION = 1


def merge_insight_sections(
    stored: Sequence[object] | None,
) -> list[SectionPreference]:
    """Resolve stored preferences with defaults for missing or unknown keys."""
    return merge_sections(
        stored,
        defaults=DEFAULT_INSIGHT_SECTIONS,
        valid_keys=VALID_INSIGHT_SECTION_KEYS,
        locked_keys=LOCKED_INSIGHT_SECTION_KEYS,
    )


def normalize_insight_sections(
    sections: Sequence[object] | None,
) -> list[SectionPreference] | None:
    """Validate and dedupe a PATCH payload; empty list is allowed.

    Locked keys (``insight_feed``) are forced to ``enabled=True``.
    """
    return normalize_sections(
        sections,
        valid_keys=VALID_INSIGHT_SECTION_KEYS,
        locked_keys=LOCKED_INSIGHT_SECTION_KEYS,
    )


def _is_exact_legacy_layout(stored: Sequence[object]) -> bool:
    """Compare the raw stored array before normalization changes locked flags."""
    return len(stored) == len(LEGACY_DEFAULT_INSIGHT_SECTIONS) and all(
        isinstance(raw, dict)
        and raw.get("key") == default["key"]
        and raw.get("enabled") is default["enabled"]
        for raw, default in zip(stored, LEGACY_DEFAULT_INSIGHT_SECTIONS, strict=True)
    )


def migrate_insight_sections_to_current(
    stored: Sequence[object] | None,
    *,
    version: int | None,
) -> tuple[list[SectionPreference] | None, int, bool]:
    """One-time v1→v2 hub shrink.

    Returns ``(sections_to_persist_or_None, new_version, dirty)``.
    ``None`` sections means leave the JSON column NULL (use defaults via merge).
    """
    current_version = version if version is not None else LEGACY_INSIGHT_SECTIONS_VERSION
    if current_version >= CURRENT_INSIGHT_SECTIONS_VERSION:
        normalized = normalize_insight_sections(stored)
        return normalized, current_version, False

    if not stored:
        # NULL/empty → new slim defaults via merge; persist version only.
        return None, CURRENT_INSIGHT_SECTIONS_VERSION, True

    normalized = normalize_insight_sections(stored) or []
    if not normalized:
        return None, CURRENT_INSIGHT_SECTIONS_VERSION, True

    if _is_exact_legacy_layout(stored):
        # Only the complete, ordered, unchanged v1 template is known to be inherited.
        return (
            [section.copy() for section in DEFAULT_INSIGHT_SECTIONS],
            CURRENT_INSIGHT_SECTIONS_VERSION,
            True,
        )

    # A partial, reordered, or changed layout is user state. Keep every explicit
    # flag and its order; append missing known keys using today's defaults.
    return merge_insight_sections(normalized), CURRENT_INSIGHT_SECTIONS_VERSION, True
