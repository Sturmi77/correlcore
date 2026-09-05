from __future__ import annotations

from app.services.insight_sections import (
    DEFAULT_INSIGHT_SECTIONS,
    merge_insight_sections,
    normalize_insight_sections,
)


def test_merge_insight_sections_returns_default_when_null() -> None:
    assert merge_insight_sections(None) == DEFAULT_INSIGHT_SECTIONS


def test_merge_insight_sections_returns_default_when_empty() -> None:
    assert merge_insight_sections([]) == DEFAULT_INSIGHT_SECTIONS


def test_merge_insight_sections_preserves_user_order() -> None:
    stored = [
        {"key": "tag_groups", "enabled": True},
        {"key": "correlation_matrix", "enabled": False},
    ]
    merged = merge_insight_sections(stored)
    assert [item["key"] for item in merged][:2] == ["tag_groups", "correlation_matrix"]
    assert merged[1]["enabled"] is False
    # Missing keys are appended from defaults.
    assert {item["key"] for item in merged} == {
        section["key"] for section in DEFAULT_INSIGHT_SECTIONS
    }


def test_merge_insight_sections_drops_unknown_keys() -> None:
    stored = [
        {"key": "legacy_block", "enabled": True},
        {"key": "lag_heatmap", "enabled": True},
    ]
    merged = merge_insight_sections(stored)
    assert "legacy_block" not in {item["key"] for item in merged}
    assert merged[0]["key"] == "lag_heatmap"


def test_merge_insight_sections_forces_locked_feed_enabled() -> None:
    # A client that stored insight_feed disabled must still get it enabled.
    stored = [{"key": "insight_feed", "enabled": False}]
    merged = merge_insight_sections(stored)
    feed = next(item for item in merged if item["key"] == "insight_feed")
    assert feed["enabled"] is True


def test_normalize_insight_sections_allows_empty_list() -> None:
    assert normalize_insight_sections([]) == []


def test_normalize_insight_sections_rejects_invalid_entries() -> None:
    stored = [
        {"key": "lag_heatmap", "enabled": True},
        {"key": "lag_heatmap", "enabled": False},
        {"key": "not_real", "enabled": True},
        {"enabled": True},
    ]
    assert normalize_insight_sections(stored) == [{"key": "lag_heatmap", "enabled": True}]


def test_normalize_insight_sections_forces_locked_feed_enabled() -> None:
    assert normalize_insight_sections([{"key": "insight_feed", "enabled": False}]) == [
        {"key": "insight_feed", "enabled": True}
    ]


def test_stage_header_is_a_default_section() -> None:
    # #823: readiness header is a regular, hideable section (default first).
    assert DEFAULT_INSIGHT_SECTIONS[0]["key"] == "stage_header"
    assert DEFAULT_INSIGHT_SECTIONS[0]["enabled"] is True


def test_stage_header_can_be_disabled() -> None:
    # Unlike insight_feed, stage_header is not locked and may be hidden.
    assert normalize_insight_sections([{"key": "stage_header", "enabled": False}]) == [
        {"key": "stage_header", "enabled": False}
    ]
    merged = merge_insight_sections([{"key": "stage_header", "enabled": False}])
    stage = next(item for item in merged if item["key"] == "stage_header")
    assert stage["enabled"] is False
