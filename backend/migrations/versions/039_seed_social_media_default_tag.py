"""039 seed missing Leisure curated default tags (#678)

Revision ID: 039
Revises: 038
Create Date: 2026-08-13

The onboarding tag suggestions (``app.services.onboarding_service._SUGGESTIONS``)
offer ``social-media`` and ``tv`` tags in the Leisure category, but migration
004 never seeded matching curated defaults (``is_default = TRUE``,
``user_id IS NULL``). Other Leisure suggestions such as ``reading`` and
``gaming`` do have curated defaults, so they show up in the tag picker for
everyone. ``social-media`` and ``tv`` did not: unless a user picked one during
onboarding — which creates a *custom* tag — they were invisible in the running
instance's tag picker.

This inserts the missing defaults so both are available to everyone, like their
Leisure siblings. Category ``leisure`` and icons match the onboarding
suggestions; colour ``#8b5cf6`` matches the Leisure defaults from 004.

Idempotent: each insert is guarded by ``WHERE NOT EXISTS`` on the curated slug,
so re-running (or running against a DB where a row somehow already exists) is a
no-op. ``ux_tags_default_slug`` also enforces one curated tag per slug.

A user who already owns a *custom* ``social-media`` / ``tv`` tag keeps it — the
two partial unique indexes (``ux_tags_default_slug`` vs ``ux_tags_user_slug``)
are independent, so the curated default and any pre-existing custom tag coexist.
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op

revision: str = "039"
down_revision: str | None = "038"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

logger = logging.getLogger("alembic.runtime.migration")

# (slug, name, category, icon, color) — mirrors the onboarding suggestions and
# the Leisure colour from migration 004.
_MISSING_DEFAULTS: tuple[tuple[str, str, str, str, str], ...] = (
    ("social-media", "Social Media", "leisure", "smartphone", "#8b5cf6"),
    ("tv", "TV", "leisure", "tv", "#8b5cf6"),
)


def upgrade() -> None:
    conn = op.get_bind()

    # ``tags`` uses ENABLE (not FORCE) ROW LEVEL SECURITY, so the table owner —
    # the role every migration runs as — bypasses the policies, exactly as the
    # bulk seed in migration 004 relied on. The INSERT policy would otherwise
    # reject ``is_default = TRUE`` rows.
    for slug, name, category, icon, color in _MISSING_DEFAULTS:
        # ``:slug`` is bound under two distinct names (``slug`` / ``slug_check``)
        # on purpose. Reusing one named parameter across the SELECT list and the
        # NOT EXISTS predicate collapses to a single ``$1``, and PostgreSQL then
        # deduces conflicting types for it — ``text`` from the bare SELECT value
        # vs ``character varying`` from the ``slug`` column comparison — which
        # aborts with "inconsistent types deduced for parameter $1". Two names
        # give two independently-typed placeholders.
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
        logger.info("039: seeded %s curated default tag(s) for slug '%s'", result.rowcount, slug)


def downgrade() -> None:
    # Remove only the curated defaults. entry_tags references cascade on delete
    # (migration 004), so any entries tagged with these *default* tags lose that
    # association; user-owned custom tags are untouched because this targets
    # ``is_default = TRUE`` only.
    conn = op.get_bind()
    slugs = [row[0] for row in _MISSING_DEFAULTS]
    conn.execute(
        sa.text("DELETE FROM tags WHERE slug = ANY(:slugs) AND is_default = TRUE"),
        {"slugs": slugs},
    )
