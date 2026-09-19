from __future__ import annotations

from app.services.insight_sections import (
    CURRENT_INSIGHT_SECTIONS_VERSION,
    DEFAULT_INSIGHT_SECTIONS,
    LEGACY_DEFAULT_INSIGHT_SECTIONS,
    merge_insight_sections,
    migrate_insight_sections_to_current,
    normalize_insight_sections,
)


def test_merge_insight_sections_returns_slim_default_when_null() -> None:
    assert merge_insight_sections(None) == DEFAULT_INSIGHT_SECTIONS
    assert DEFAULT_INSIGHT_SECTIONS[0]["key"] == "stage_header"
    assert next(s for s in DEFAULT_INSIGHT_SECTIONS if s["key"] == "correlation_matrix")[
        "enabled"
    ] is False


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
    assert DEFAULT_INSIGHT_SECTIONS[0]["key"] == "stage_header"
    assert DEFAULT_INSIGHT_SECTIONS[0]["enabled"] is True


def test_stage_header_can_be_disabled() -> None:
    assert normalize_insight_sections([{"key": "stage_header", "enabled": False}]) == [
        {"key": "stage_header", "enabled": False}
    ]
    merged = merge_insight_sections([{"key": "stage_header", "enabled": False}])
    stage = next(item for item in merged if item["key"] == "stage_header")
    assert stage["enabled"] is False


def test_migrate_replaces_exact_legacy_defaults() -> None:
    sections, version, dirty = migrate_insight_sections_to_current(
        LEGACY_DEFAULT_INSIGHT_SECTIONS,
        version=1,
    )
    assert dirty is True
    assert version == CURRENT_INSIGHT_SECTIONS_VERSION
    assert sections == DEFAULT_INSIGHT_SECTIONS


def test_migrate_preserves_explicit_off_while_shrinking_inherited_ons() -> None:
    stored = [
        {"key": "stage_header", "enabled": True},
        {"key": "correlation_matrix", "enabled": True},
        {"key": "insight_feed", "enabled": True},
        {"key": "lag_heatmap", "enabled": False},
        {"key": "dismissed", "enabled": True},
        {"key": "symptom_analytics", "enabled": True},
        {"key": "tag_groups", "enabled": True},
        {"key": "tag_cooccurrence", "enabled": True},
    ]
    sections, version, dirty = migrate_insight_sections_to_current(stored, version=1)
    assert dirty is True
    assert version == CURRENT_INSIGHT_SECTIONS_VERSION
    assert sections is not None
    by_key = {item["key"]: item["enabled"] for item in sections}
    assert by_key["lag_heatmap"] is False
    assert by_key["correlation_matrix"] is False
    assert by_key["insight_feed"] is True


def test_migrate_noop_when_already_current() -> None:
    sections, version, dirty = migrate_insight_sections_to_current(
        LEGACY_DEFAULT_INSIGHT_SECTIONS,
        version=CURRENT_INSIGHT_SECTIONS_VERSION,
    )
    assert dirty is False
    assert version == CURRENT_INSIGHT_SECTIONS_VERSION


def test_migrate_empty_only_bumps_version() -> None:
    sections, version, dirty = migrate_insight_sections_to_current(None, version=1)
    assert dirty is True
    assert sections is None
    assert version == CURRENT_INSIGHT_SECTIONS_VERSION
