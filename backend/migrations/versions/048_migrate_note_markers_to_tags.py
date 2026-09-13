"""048 migrate note markers to tags (#895)

Revision ID: 048
Revises: 047
Create Date: 2026-09-13

Data migration for the #890 consolidation (Option 4 — one label system).
After #893 removed the note-marker capture UI, this backfills the tag system
from existing ``entry_note_markers`` so context lives in one place:

- **Predefined 1:1** markers with a clean single-tag target are linked to the
  existing curated default tag: ``conflict``, ``travel``, ``achievement``.
- **Custom** markers (anything not in the predefined taxonomy) become per-user
  **custom tags** (category ``other``), then linked. Slugs are derived to the
  strict tag-slug format; un-sluggable markers (< 2 usable chars) are skipped.
  A custom marker is only ever linked to the **user's own** tag or a newly
  created one — never silently attached to a curated default; if its derived
  slug would shadow a curated default it is skipped (mirrors ``create_custom_tag``).
- **Generic / overlap** predefined markers are **intentionally skipped**
  (``work``, ``homeoffice``, ``social``, ``movement``, ``sleep_bad``,
  ``sleep_good``, ``stress``, ``symptom``) — they duplicate ``work_context``,
  the sliders, the SymptomChecker, or whole tag categories, and are dominated
  by those surfaces (see #890 analysis / follow-up #897). ``social`` and
  ``movement`` map to tag *categories*, not a single tag, so converting them
  would fabricate specificity.

Policy: **additive, idempotent, non-destructive.** Only ``entry_tags`` links
(and custom ``tags`` rows) are inserted, each guarded so a re-run is a no-op.
Existing ``entry_note_markers`` rows are **kept** — their fate (analytics
overhaul / UI + taxonomy retirement) is decided in #896 / #897. Slug stability
of existing tags is preserved (contract toward the burnout analysis, #875).

Downgrade is a deliberate no-op: the inserted links/tags cannot be told apart
from user-created ones after the fact, so reversing would risk deleting
legitimate user data.
"""

from __future__ import annotations

import logging
import re
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "048"
down_revision: str | None = "047"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

logger = logging.getLogger("alembic.runtime.migration")

# Predefined markers with an unambiguous 1:1 curated default-tag target.
_PREDEFINED_TAG_MAP: dict[str, str] = {
    "conflict": "conflict",
    "travel": "travel",
    "achievement": "achievement",
}

# Full predefined taxonomy (schemas/note.py). Anything outside this set is a
# custom marker; predefined keys not in _PREDEFINED_TAG_MAP are skipped.
_PREDEFINED_MARKERS: frozenset[str] = frozenset(
    {
        "work",
        "homeoffice",
        "social",
        "movement",
        "sleep_bad",
        "sleep_good",
        "stress",
        "conflict",
        "symptom",
        "travel",
        "achievement",
    }
)

_SLUG_INVALID = re.compile(r"[^a-z0-9]+")


def derive_custom_tag_slug(marker: str) -> str | None:
    """Derive a valid tag slug from a normalised note marker.

    Tag slugs are lowercase letters/digits/dashes/underscores, 2..64 chars,
    with no repeated separators (schemas/tag.py). Note markers are already
    lowercased/whitespace-collapsed but may contain spaces or punctuation and
    can be a single character. Non-``[a-z0-9]`` runs collapse to one dash;
    returns ``None`` when fewer than 2 usable characters remain.
    """
    slug = _SLUG_INVALID.sub("-", marker).strip("-")
    if len(slug) < 2:
        return None
    return slug[:64]


def upgrade() -> None:
    conn = op.get_bind()

    # `tags` and `entry_tags` run under FORCE ROW LEVEL SECURITY (migration 012)
    # with policies keyed on `app.current_user_id`, which no migration sets. A
    # role that neither bypasses RLS nor is superuser would INSERT zero rows and
    # report success — a silent no-op nobody would notice. Fail loudly instead
    # (mirrors migration 031).
    privileged = conn.execute(
        sa.text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user")
    ).scalar()
    if not privileged:
        raise RuntimeError(
            "Migration 048 must run as a superuser or a BYPASSRLS role: tags and "
            "entry_tags enforce FORCE ROW LEVEL SECURITY, so a restricted role would "
            "silently write nothing. Run migrations as the database owner (the same "
            "role used for every earlier migration)."
        )

    # 1) Predefined 1:1 markers → link to the existing curated default tag.
    for marker, slug in _PREDEFINED_TAG_MAP.items():
        result = conn.execute(
            sa.text(
                """
                INSERT INTO entry_tags (entry_id, tag_id, user_id, created_at)
                SELECT m.entry_id, t.id, m.user_id, now()
                FROM entry_note_markers m
                JOIN tags t ON t.slug = :slug AND t.is_default = TRUE
                WHERE m.marker = :marker
                  AND NOT EXISTS (
                    SELECT 1 FROM entry_tags et
                    WHERE et.entry_id = m.entry_id AND et.tag_id = t.id
                  )
                """
            ),
            {"marker": marker, "slug": slug},
        )
        logger.info("048: linked %s entries for predefined marker '%s'", result.rowcount, marker)

    # 2) Custom markers → per-user custom tags, then link.
    custom_rows = conn.execute(
        sa.text(
            """
            SELECT DISTINCT user_id, marker
            FROM entry_note_markers
            WHERE marker NOT IN :predefined
            """
        ).bindparams(sa.bindparam("predefined", expanding=True)),
        {"predefined": list(_PREDEFINED_MARKERS)},
    ).fetchall()

    created = linked = skipped = 0
    for user_id, marker in custom_rows:
        slug = derive_custom_tag_slug(marker)
        if slug is None:
            skipped += 1
            logger.info("048: skipped un-sluggable custom marker '%s'", marker)
            continue

        # Reuse only the user's OWN tag with this slug — never attach to a
        # curated default: silently merging custom context onto the global
        # taxonomy is irreversible and surprising (#899 review). If the derived
        # slug would shadow a curated default, skip (mirrors create_custom_tag,
        # which forbids such customs) rather than create or global-merge.
        tag_id = conn.execute(
            sa.text("SELECT id FROM tags WHERE slug = :slug AND user_id = :uid LIMIT 1"),
            {"slug": slug, "uid": user_id},
        ).scalar()

        if tag_id is None:
            clashes_default = conn.execute(
                sa.text("SELECT 1 FROM tags WHERE slug = :slug AND is_default = TRUE LIMIT 1"),
                {"slug": slug},
            ).scalar()
            if clashes_default:
                skipped += 1
                logger.info(
                    "048: skipped custom marker '%s' (slug '%s' clashes with a default tag)",
                    marker,
                    slug,
                )
                continue
            tag_id = uuid.uuid4()
            conn.execute(
                sa.text(
                    """
                    INSERT INTO tags (
                        id, user_id, slug, name, category,
                        is_default, is_hidden, include_in_analytics, habit_type
                    )
                    VALUES (
                        CAST(:id AS uuid), :uid, :slug, :name, CAST('other' AS tag_category),
                        FALSE, FALSE, TRUE, 'none'
                    )
                    """
                ),
                {"id": str(tag_id), "uid": user_id, "slug": slug, "name": marker[:64]},
            )
            created += 1

        result = conn.execute(
            sa.text(
                """
                INSERT INTO entry_tags (entry_id, tag_id, user_id, created_at)
                SELECT m.entry_id, CAST(:tag_id AS uuid), m.user_id, now()
                FROM entry_note_markers m
                WHERE m.user_id = :uid AND m.marker = :marker
                  AND NOT EXISTS (
                    SELECT 1 FROM entry_tags et
                    WHERE et.entry_id = m.entry_id AND et.tag_id = CAST(:tag_id AS uuid)
                  )
                """
            ),
            {"tag_id": str(tag_id), "uid": user_id, "marker": marker},
        )
        linked += result.rowcount

    logger.info(
        "048: custom markers → tags: %s tag(s) created, %s link(s) added, %s skipped",
        created,
        linked,
        skipped,
    )


def downgrade() -> None:
    # Deliberate no-op: inserted links/custom tags are indistinguishable from
    # user-created ones after the fact; reversing would risk deleting
    # legitimate user data. The source `entry_note_markers` rows are untouched
    # by this migration, so no data is lost by not reversing.
    pass
