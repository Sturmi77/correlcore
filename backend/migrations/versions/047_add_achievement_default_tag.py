"""047 add achievement default tag

Revision ID: 047
Revises: 046
Create Date: 2026-09-13

Seeds the curated ``achievement`` default tag ("Erfolg") introduced in
``app.data.tag_catalog``. This is the one former note-marker (#890) with no
parallel tag/field, and doubles as the positive recovery signal for the
burnout analysis (#875). Existing entries keep their tags untouched.

Idempotent: the insert is guarded with ``WHERE NOT EXISTS`` on the curated
slug, so re-running is a no-op.
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op

revision: str = "047"
down_revision: str | None = "046"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

logger = logging.getLogger("alembic.runtime.migration")

# (slug, name, category, icon, color) — mirrors DefaultTagSpec in tag_catalog.
_NEW_DEFAULT_TAGS: tuple[tuple[str, str, str, str, str], ...] = (
    ("achievement", "Erfolg", "other", "trophy", "#64748b"),
)


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
        logger.info("047: seeded %s curated default tag(s) for slug '%s'", result.rowcount, slug)


def downgrade() -> None:
    conn = op.get_bind()
    tag_slugs = [row[0] for row in _NEW_DEFAULT_TAGS]
    conn.execute(
        sa.text("DELETE FROM tags WHERE slug = ANY(:slugs) AND is_default = TRUE"),
        {"slugs": tag_slugs},
    )
