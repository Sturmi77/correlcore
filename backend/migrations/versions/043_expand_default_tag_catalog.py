"""043 expand curated tag catalogue and physiological symptoms

Revision ID: 043
Revises: 042
Create Date: 2026-08-25

Aligns seeded defaults with the canonical catalogue in
``app.data.tag_catalog``:

- Insert lifestyle tags that onboarding already suggested (walk, cycle,
  period, pms, alone-time, weather, news) plus high-frequency journal
  tags (stretching, screen-time, cooking, housework, sick-day).
- Fix display names on existing defaults (Krafttraining typo; caffeine /
  sugar / meetings no longer intensity-coded in the label).
- Seed three additional physiological default symptoms (migraine, nausea,
  dizziness). Mental-health keys stay out of the curated set.

Idempotent: inserts are guarded with ``WHERE NOT EXISTS`` on the curated
slug. Name updates only touch ``is_default = TRUE`` rows.
"""

from __future__ import annotations

import logging
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "043"
down_revision: str | None = "042"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

logger = logging.getLogger("alembic.runtime.migration")

# (slug, name, category, icon, color) — new curated defaults only.
_NEW_DEFAULT_TAGS: tuple[tuple[str, str, str, str, str], ...] = (
    ("stretching", "Dehnen", "sport", "person-standing", "#10b981"),
    ("alone-time", "Alleinzeit", "social", "user", "#3b82f6"),
    ("screen-time", "Bildschirmzeit", "leisure", "monitor", "#8b5cf6"),
    ("cooking", "Kochen", "leisure", "cooking-pot", "#8b5cf6"),
    ("walk", "Spaziergang", "health", "footprints", "#14b8a6"),
    ("sick-day", "Krankheitstag", "health", "thermometer", "#14b8a6"),
    ("cycle", "Zyklus", "cycle", "rotate-cw", "#0d9488"),
    ("period", "Periode", "cycle", "droplet", "#0d9488"),
    ("pms", "PMS", "cycle", "cloud-fog", "#0d9488"),
    ("housework", "Haushalt", "other", "house", "#64748b"),
    ("weather", "Wetter", "other", "cloud-sun", "#64748b"),
    ("news", "Nachrichten", "other", "newspaper", "#64748b"),
)

# (slug, new German display name)
_RENAME_DEFAULTS: tuple[tuple[str, str], ...] = (
    ("strength", "Krafttraining"),
    ("meeting_heavy", "Meetings"),
    ("caffeine_high", "Koffein"),
    ("sugar_high", "Zucker"),
    ("social-media", "Soziale Medien"),
)

# (slug, German name, emoji icon) — physiological only.
_NEW_DEFAULT_SYMPTOMS: tuple[tuple[str, str, str], ...] = (
    ("migraine", "Migräne", "🤯"),
    ("nausea", "Übelkeit", "🤢"),
    ("dizziness", "Schwindel", "😵"),
)


def _default_symptom_uuid(slug: str) -> uuid.UUID:
    """Mirror of ``app.models.symptom.default_symptom_uuid``."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"moodsync.symptom.{slug}")


def upgrade() -> None:
    conn = op.get_bind()

    for slug, name, category, icon, color in _NEW_DEFAULT_TAGS:
        result = conn.execute(
            sa.text(
                """
                INSERT INTO tags (slug, name, category, icon, color, is_default, user_id)
                SELECT :slug, :name, CAST(:category AS tag_category), :icon, :color, TRUE, NULL
                WHERE NOT EXISTS (
                    SELECT 1 FROM tags WHERE slug = :slug_check AND is_default = TRUE
                )
                """
            ),
            {
                "slug": slug,
                "slug_check": slug,
                "name": name,
                "category": category,
                "icon": icon,
                "color": color,
            },
        )
        logger.info("043: seeded %s curated default tag(s) for slug '%s'", result.rowcount, slug)

    for slug, name in _RENAME_DEFAULTS:
        result = conn.execute(
            sa.text(
                """
                UPDATE tags
                SET name = :name, updated_at = now()
                WHERE slug = :slug AND is_default = TRUE AND name IS DISTINCT FROM :name
                """
            ),
            {"slug": slug, "name": name},
        )
        logger.info("043: renamed %s curated default tag(s) for slug '%s'", result.rowcount, slug)

    for slug, name, icon in _NEW_DEFAULT_SYMPTOMS:
        result = conn.execute(
            sa.text(
                """
                INSERT INTO symptoms (id, slug, name, icon, is_default, user_id)
                SELECT CAST(:id AS uuid), :slug, :name, :icon, TRUE, NULL
                WHERE NOT EXISTS (
                    SELECT 1 FROM symptoms WHERE slug = :slug_check AND is_default = TRUE
                )
                """
            ),
            {
                "id": str(_default_symptom_uuid(slug)),
                "slug": slug,
                "slug_check": slug,
                "name": name,
                "icon": icon,
            },
        )
        logger.info(
            "043: seeded %s curated default symptom(s) for slug '%s'", result.rowcount, slug
        )


def downgrade() -> None:
    conn = op.get_bind()
    tag_slugs = [row[0] for row in _NEW_DEFAULT_TAGS]
    conn.execute(
        sa.text("DELETE FROM tags WHERE slug = ANY(:slugs) AND is_default = TRUE"),
        {"slugs": tag_slugs},
    )
    symptom_slugs = [row[0] for row in _NEW_DEFAULT_SYMPTOMS]
    conn.execute(
        sa.text("DELETE FROM symptoms WHERE slug = ANY(:slugs) AND is_default = TRUE"),
        {"slugs": symptom_slugs},
    )
    conn.execute(
        sa.text(
            """
            UPDATE tags SET name = 'Kraftraining', updated_at = now()
            WHERE slug = 'strength' AND is_default = TRUE
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE tags SET name = 'Viele Meetings', updated_at = now()
            WHERE slug = 'meeting_heavy' AND is_default = TRUE
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE tags SET name = 'Viel Koffein', updated_at = now()
            WHERE slug = 'caffeine_high' AND is_default = TRUE
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE tags SET name = 'Viel Zucker', updated_at = now()
            WHERE slug = 'sugar_high' AND is_default = TRUE
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE tags SET name = 'Social Media', updated_at = now()
            WHERE slug = 'social-media' AND is_default = TRUE
            """
        )
    )
