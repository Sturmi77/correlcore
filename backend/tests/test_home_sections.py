from __future__ import annotations

import pytest

from app.services.home_sections import (
    DEFAULT_HOME_SECTIONS,
    merge_home_sections,
    normalize_home_sections,
)


def test_merge_home_sections_returns_default_when_null() -> None:
    assert merge_home_sections(None) == DEFAULT_HOME_SECTIONS


def test_merge_home_sections_returns_default_when_empty() -> None:
    assert merge_home_sections([]) == DEFAULT_HOME_SECTIONS


def test_merge_home_sections_preserves_user_order() -> None:
    stored = [
        {"key": "weekday_overview", "enabled": True},
        {"key": "daily_brief", "enabled": False},
    ]
    merged = merge_home_sections(stored)
    assert [item["key"] for item in merged] == [
        "weekday_overview",
        "daily_brief",
        "first_week_banner",
        "work_context",
    ]
    assert merged[1]["enabled"] is False


def test_merge_home_sections_drops_unknown_keys() -> None:
    stored = [
        {"key": "legacy_block", "enabled": True},
        {"key": "daily_brief", "enabled": True},
    ]
    merged = merge_home_sections(stored)
    assert "legacy_block" not in {item["key"] for item in merged}
    assert merged[0]["key"] == "daily_brief"


def test_normalize_home_sections_allows_empty_list() -> None:
    assert normalize_home_sections([]) == []


def test_normalize_home_sections_rejects_invalid_entries() -> None:
    stored = [
        {"key": "daily_brief", "enabled": True},
        {"key": "daily_brief", "enabled": False},
        {"key": "not_real", "enabled": True},
        {"enabled": True},
    ]
    assert normalize_home_sections(stored) == [{"key": "daily_brief", "enabled": True}]
