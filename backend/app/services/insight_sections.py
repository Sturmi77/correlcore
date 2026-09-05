"""Insights page section preferences (#821).

Configurable order and visibility for the ``/insights`` page blocks, mirroring
the Home screen mechanism (#584). The main insight feed (``insight_feed``) is a
locked section: always enabled (never hidden), but freely reorderable.
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


DEFAULT_INSIGHT_SECTIONS: list[SectionPreference] = [
    {"key": "correlation_matrix", "enabled": True},
    {"key": "insight_feed", "enabled": True},
    {"key": "lag_heatmap", "enabled": True},
    {"key": "dismissed", "enabled": True},
    {"key": "symptom_analytics", "enabled": True},
    {"key": "tag_groups", "enabled": True},
    {"key": "tag_cooccurrence", "enabled": True},
]


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
