"""Canonical curated tag catalogue.

One source of truth for default-tag slugs, display names, categories, and
which of those tags appear in onboarding. Migrations seed independently
(Alembic must not import app code) and must stay in sync with this module.

Research inputs (public taxonomies, not scraped journals):
- Daylio-style activity groups (social, sleep, hobbies, food, chores)
- Bearable-style lifestyle factors (movement, consumption, symptoms)
- Quantified-Self / self-optimizer write-ups: sleep, caffeine, alcohol,
  daylight/walks, screen time, training, cycle, routine disruption (travel)

Kept out of the global defaults (optional custom tags only): cold plunge,
zone-2, nootropics, fasting windows, supplement stacks. Those belong to a
lab-QS workflow, not a 60-second lifestyle check-in.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.tag import TagCategory
from app.schemas.onboarding import TagSuggestion, TagSuggestionGroup

# Stored hex values match the category colours from migration 004, plus
# cycle / other which were added later.
_SPORT = "#10b981"
_SOCIAL = "#3b82f6"
_WORK = "#f59e0b"
_LEISURE = "#8b5cf6"
_CONSUMPTION = "#dc2626"
_HEALTH = "#14b8a6"
_CYCLE = "#0d9488"
_OTHER = "#64748b"


@dataclass(frozen=True)
class DefaultTagSpec:
    """One curated default tag."""

    slug: str
    name_de: str
    name_en: str
    category: TagCategory
    icon: str
    color: str
    onboarding: bool = False


# Existing slugs are stable keys. New lifestyle tags fill gaps that onboarding
# already offered (or that journals actually use) without exploding the picker.
DEFAULT_TAGS: tuple[DefaultTagSpec, ...] = (
    # Sport
    DefaultTagSpec("sport", "Sport", "Sport", TagCategory.SPORT, "dumbbell", _SPORT),
    DefaultTagSpec(
        "running", "Laufen", "Running", TagCategory.SPORT, "footprints", _SPORT, onboarding=True
    ),
    DefaultTagSpec("cycling", "Radfahren", "Cycling", TagCategory.SPORT, "bike", _SPORT),
    DefaultTagSpec("yoga", "Yoga", "Yoga", TagCategory.SPORT, "flower", _SPORT, onboarding=True),
    DefaultTagSpec(
        "strength",
        "Krafttraining",
        "Strength training",
        TagCategory.SPORT,
        "dumbbell",
        _SPORT,
        onboarding=True,
    ),
    DefaultTagSpec(
        "stretching",
        "Dehnen",
        "Stretching",
        TagCategory.SPORT,
        "person-standing",
        _SPORT,
        onboarding=True,
    ),
    # Social
    DefaultTagSpec(
        "family", "Familie", "Family", TagCategory.SOCIAL, "users", _SOCIAL, onboarding=True
    ),
    DefaultTagSpec(
        "friends", "Freunde", "Friends", TagCategory.SOCIAL, "users", _SOCIAL, onboarding=True
    ),
    DefaultTagSpec("partner", "Partner:in", "Partner", TagCategory.SOCIAL, "heart", _SOCIAL),
    DefaultTagSpec(
        "conflict", "Konflikt", "Conflict", TagCategory.SOCIAL, "alert-triangle", "#ef4444"
    ),
    DefaultTagSpec("date", "Date", "Date", TagCategory.SOCIAL, "heart", _SOCIAL),
    DefaultTagSpec(
        "alone-time",
        "Alleinzeit",
        "Alone time",
        TagCategory.SOCIAL,
        "user",
        _SOCIAL,
        onboarding=True,
    ),
    # Work
    DefaultTagSpec(
        "work_intense", "Arbeit intensiv", "Intense work", TagCategory.WORK, "briefcase", _WORK
    ),
    DefaultTagSpec(
        "meeting_heavy",
        "Meetings",
        "Meetings",
        TagCategory.WORK,
        "calendar",
        _WORK,
        onboarding=True,
    ),
    DefaultTagSpec(
        "focus_time",
        "Fokus-Zeit",
        "Deep work",
        TagCategory.WORK,
        "target",
        _WORK,
        onboarding=True,
    ),
    DefaultTagSpec("commute", "Pendeln", "Commute", TagCategory.WORK, "train", _WORK),
    DefaultTagSpec(
        "deadline", "Deadline", "Deadline", TagCategory.WORK, "alarm-clock", _WORK, onboarding=True
    ),
    # Leisure
    DefaultTagSpec("music", "Musik", "Music", TagCategory.LEISURE, "music", _LEISURE),
    DefaultTagSpec(
        "reading", "Lesen", "Reading", TagCategory.LEISURE, "book-open", _LEISURE, onboarding=True
    ),
    DefaultTagSpec(
        "gaming", "Gaming", "Gaming", TagCategory.LEISURE, "gamepad-2", _LEISURE, onboarding=True
    ),
    DefaultTagSpec("nature", "Natur", "Nature", TagCategory.LEISURE, "tree-pine", _LEISURE),
    DefaultTagSpec(
        "travel", "Reisen", "Travel", TagCategory.LEISURE, "plane", _LEISURE, onboarding=True
    ),
    DefaultTagSpec("tv", "TV", "TV", TagCategory.LEISURE, "tv", _LEISURE),
    DefaultTagSpec(
        "social-media",
        "Soziale Medien",
        "Social media",
        TagCategory.LEISURE,
        "smartphone",
        _LEISURE,
        onboarding=True,
    ),
    DefaultTagSpec(
        "screen-time",
        "Bildschirmzeit",
        "Screen time",
        TagCategory.LEISURE,
        "monitor",
        _LEISURE,
        onboarding=True,
    ),
    DefaultTagSpec("cooking", "Kochen", "Cooking", TagCategory.LEISURE, "cooking-pot", _LEISURE),
    # Consumption
    DefaultTagSpec(
        "alcohol",
        "Alkohol",
        "Alcohol",
        TagCategory.CONSUMPTION,
        "wine",
        _CONSUMPTION,
        onboarding=True,
    ),
    DefaultTagSpec(
        "caffeine_high",
        "Koffein",
        "Caffeine",
        TagCategory.CONSUMPTION,
        "coffee",
        _CONSUMPTION,
        onboarding=True,
    ),
    DefaultTagSpec(
        "sugar_high",
        "Zucker",
        "Sugar",
        TagCategory.CONSUMPTION,
        "candy",
        _CONSUMPTION,
        onboarding=True,
    ),
    DefaultTagSpec(
        "fast_food", "Fast Food", "Fast food", TagCategory.CONSUMPTION, "pizza", _CONSUMPTION
    ),
    DefaultTagSpec(
        "nicotine", "Nikotin", "Nicotine", TagCategory.CONSUMPTION, "cigarette", _CONSUMPTION
    ),
    # Health
    DefaultTagSpec("meditation", "Meditation", "Meditation", TagCategory.HEALTH, "brain", _HEALTH),
    DefaultTagSpec(
        "therapy",
        "Therapie",
        "Therapy",
        TagCategory.HEALTH,
        "stethoscope",
        _HEALTH,
        onboarding=True,
    ),
    DefaultTagSpec(
        "medication",
        "Medikament",
        "Medication",
        TagCategory.HEALTH,
        "pill",
        _HEALTH,
        onboarding=True,
    ),
    DefaultTagSpec("good_sleep", "Guter Schlaf", "Good sleep", TagCategory.HEALTH, "moon", _HEALTH),
    DefaultTagSpec("nap", "Mittagsschlaf", "Nap", TagCategory.HEALTH, "bed", _HEALTH),
    DefaultTagSpec(
        "walk", "Spaziergang", "Walk", TagCategory.HEALTH, "footprints", _HEALTH, onboarding=True
    ),
    DefaultTagSpec(
        "sick-day",
        "Krankheitstag",
        "Sick day",
        TagCategory.HEALTH,
        "thermometer",
        _HEALTH,
        onboarding=True,
    ),
    # Cycle
    DefaultTagSpec(
        "cycle", "Zyklus", "Cycle", TagCategory.CYCLE, "rotate-cw", _CYCLE, onboarding=True
    ),
    DefaultTagSpec(
        "period", "Periode", "Period", TagCategory.CYCLE, "droplet", _CYCLE, onboarding=True
    ),
    DefaultTagSpec("pms", "PMS", "PMS", TagCategory.CYCLE, "cloud-fog", _CYCLE, onboarding=True),
    # Other
    DefaultTagSpec(
        "housework", "Haushalt", "Housework", TagCategory.OTHER, "house", _OTHER, onboarding=True
    ),
    DefaultTagSpec(
        "weather", "Wetter", "Weather", TagCategory.OTHER, "cloud-sun", _OTHER, onboarding=True
    ),
    DefaultTagSpec(
        "news", "Nachrichten", "News", TagCategory.OTHER, "newspaper", _OTHER, onboarding=True
    ),
)

# Onboarding historically used friendlier slugs than the seeded defaults.
# Map those onto the canonical default so a stale client does not create a
# duplicate custom tag.
ONBOARDING_SLUG_ALIASES: dict[str, str] = {
    "strength-training": "strength",
    "deep-work": "focus_time",
    "meetings": "meeting_heavy",
    "caffeine": "caffeine_high",
    "sugar": "sugar_high",
}

# Category order for the onboarding picker.
_ONBOARDING_CATEGORY_ORDER: tuple[TagCategory, ...] = (
    TagCategory.SPORT,
    TagCategory.WORK,
    TagCategory.HEALTH,
    TagCategory.SOCIAL,
    TagCategory.CYCLE,
    TagCategory.LEISURE,
    TagCategory.CONSUMPTION,
    TagCategory.OTHER,
)


def default_tags_by_slug() -> dict[str, DefaultTagSpec]:
    """Return the catalogue keyed by slug."""
    return {spec.slug: spec for spec in DEFAULT_TAGS}


def canonical_onboarding_slug(slug: str) -> str:
    """Resolve a legacy onboarding slug onto the curated default slug."""
    return ONBOARDING_SLUG_ALIASES.get(slug, slug)


def onboarding_suggestion_groups() -> tuple[TagSuggestionGroup, ...]:
    """Grouped onboarding suggestions, always a subset of ``DEFAULT_TAGS``."""
    grouped: dict[TagCategory, list[TagSuggestion]] = {
        cat: [] for cat in _ONBOARDING_CATEGORY_ORDER
    }
    for spec in DEFAULT_TAGS:
        if not spec.onboarding:
            continue
        grouped[spec.category].append(
            TagSuggestion(
                slug=spec.slug,
                name=spec.name_en,
                category=spec.category,
                icon=spec.icon,
                color=spec.color,
            )
        )
    return tuple(
        TagSuggestionGroup(category=category, suggestions=suggestions)
        for category, suggestions in grouped.items()
        if suggestions
    )
