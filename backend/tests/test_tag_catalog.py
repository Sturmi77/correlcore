"""Canonical tag catalogue invariants."""

from __future__ import annotations

from app.data.tag_catalog import (
    DEFAULT_TAGS,
    ONBOARDING_SLUG_ALIASES,
    canonical_onboarding_slug,
    default_tags_by_slug,
    onboarding_suggestion_groups,
)
from app.models.tag import TagCategory


def test_default_tag_slugs_are_unique() -> None:
    slugs = [spec.slug for spec in DEFAULT_TAGS]
    assert len(slugs) == len(set(slugs))


def test_onboarding_slugs_are_subset_of_defaults() -> None:
    defaults = default_tags_by_slug()
    for group in onboarding_suggestion_groups():
        assert group.suggestions, f"{group.category} onboarding group is empty"
        for suggestion in group.suggestions:
            assert suggestion.slug in defaults
            spec = defaults[suggestion.slug]
            assert suggestion.category == spec.category
            assert spec.onboarding is True


def test_onboarding_covers_every_category() -> None:
    categories = {group.category for group in onboarding_suggestion_groups()}
    assert categories == set(TagCategory)


def test_alias_targets_exist_and_are_not_self_cycles() -> None:
    defaults = default_tags_by_slug()
    for source, target in ONBOARDING_SLUG_ALIASES.items():
        assert source != target
        assert target in defaults
        assert canonical_onboarding_slug(source) == target
        assert canonical_onboarding_slug(target) == target


def test_legacy_onboarding_slugs_resolve_to_seeded_defaults() -> None:
    assert canonical_onboarding_slug("strength-training") == "strength"
    assert canonical_onboarding_slug("deep-work") == "focus_time"
    assert canonical_onboarding_slug("meetings") == "meeting_heavy"
    assert canonical_onboarding_slug("caffeine") == "caffeine_high"
    assert canonical_onboarding_slug("walk") == "walk"
