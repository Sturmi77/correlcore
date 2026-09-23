"""Transaction-local marker conversion for migration 049.

This code intentionally uses only columns present at revision 049. It never
loads the current ORM models or encrypted note content. A failure rolls back
the backfill, revision log and DROP together with Alembic's transaction.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections import defaultdict
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.engine import Connection

logger = logging.getLogger("alembic.runtime.migration")

_ONE_TO_ONE = frozenset({"conflict", "travel", "achievement"})
_OVERLAP = frozenset(
    {"work", "homeoffice", "social", "movement", "sleep_bad", "sleep_good", "stress", "symptom"}
)
_MAX_TAGS_PER_ENTRY = 50  # schema/tag.py at revision 049
_SLUG_INVALID = re.compile(r"[^a-z0-9]+")
_RLS_TABLES = (
    "entries",
    "entry_note_markers",
    "entry_symptoms",
    "entry_tags",
    "sync_revision_log",
    "sync_user_revisions",
    "tags",
)


def _slug(marker: str) -> str | None:
    slug = _SLUG_INVALID.sub("-", marker.lower()).strip("-")[:64].rstrip("-")
    return slug if len(slug) >= 2 else None


def _unique_slug(base: str, marker: str, default_slugs: set[str], claimed: dict[str, str]) -> str:
    number = 1
    while True:
        candidate = base if number == 1 else f"{base[:61].rstrip('-')}-{number}"
        owner = claimed.get(candidate)
        if candidate not in default_slugs and owner in (None, marker):
            claimed[candidate] = marker
            return candidate
        number += 1


def _revision(
    conn: Connection,
    user_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    payload: dict[str, object],
    updated_at: datetime,
) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO sync_user_revisions (user_id, current_rev) VALUES (:user_id, 0) "
            "ON CONFLICT (user_id) DO NOTHING"
        ),
        {"user_id": user_id},
    )
    user_rev = conn.execute(
        sa.text(
            "UPDATE sync_user_revisions SET current_rev = current_rev + 1, "
            "updated_at = now() WHERE user_id = :user_id RETURNING current_rev"
        ),
        {"user_id": user_id},
    ).scalar_one()
    conn.execute(
        sa.text(
            "INSERT INTO sync_revision_log "
            "(user_id, user_rev, entity_type, entity_id, operation, payload, entity_updated_at) "
            "VALUES (:user_id, :user_rev, :entity_type, :entity_id, 'upsert', "
            "CAST(:payload AS jsonb), :updated_at)"
        ),
        {
            "user_id": user_id,
            "user_rev": user_rev,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "payload": json.dumps(payload),
            "updated_at": updated_at,
        },
    )


def _tag_for_marker(
    conn: Connection,
    user_id: uuid.UUID,
    marker: str,
    default_slugs: set[str],
    claimed: dict[str, str],
    marker_slugs: dict[str, str],
) -> tuple[uuid.UUID | None, bool]:
    """Return visible target tag and whether a custom tag was created."""
    if marker in _OVERLAP:
        return None, False
    if marker in _ONE_TO_ONE:
        row = conn.execute(
            sa.text(
                "SELECT id, is_hidden FROM tags WHERE user_id = :user_id "
                "AND slug = :slug AND is_default = false "
                "UNION ALL SELECT id, is_hidden FROM tags WHERE slug = :slug "
                "AND is_default = true AND NOT EXISTS "
                "(SELECT 1 FROM tags WHERE user_id = :user_id AND slug = :slug "
                "AND is_default = false) LIMIT 1"
            ),
            {"user_id": user_id, "slug": marker},
        ).first()
        if row is None:
            raise RuntimeError("049: missing curated tag for a 1:1 marker")
        return (None if row.is_hidden else row.id), False

    slug = marker_slugs.get(marker)
    if slug is None:
        base = _slug(marker)
        if base is None:
            return None, False
        slug = _unique_slug(base, marker, default_slugs, claimed)
        marker_slugs[marker] = slug
    own = conn.execute(
        sa.text(
            "SELECT id, is_hidden FROM tags WHERE user_id = :user_id "
            "AND slug = :slug AND is_default = false"
        ),
        {"user_id": user_id, "slug": slug},
    ).first()
    if own is not None:
        return (None if own.is_hidden else own.id), False

    tag_id = uuid.uuid4()
    now = datetime.now(UTC)
    conn.execute(
        sa.text(
            "INSERT INTO tags (id, user_id, slug, name, category, is_default) "
            "VALUES (:id, :user_id, :slug, :name, CAST('other' AS tag_category), false)"
        ),
        {"id": tag_id, "user_id": user_id, "slug": slug, "name": marker[:64]},
    )
    _revision(
        conn,
        user_id,
        "tag",
        tag_id,
        {
            "slug": slug,
            "name": marker[:64],
            "category": "other",
            "icon": None,
            "color": None,
            "habit_type": "none",
            "target_frequency": None,
        },
        now,
    )
    return tag_id, True


def _entry_revision(conn: Connection, user_id: uuid.UUID, entry_id: uuid.UUID) -> None:
    updated_at = conn.execute(
        sa.text(
            "UPDATE entries SET updated_at = now() WHERE id = :entry_id "
            "AND user_id = :user_id RETURNING updated_at"
        ),
        {"entry_id": entry_id, "user_id": user_id},
    ).scalar_one()
    entry = (
        conn.execute(
            sa.text(
                "SELECT entry_date, slot::text AS slot, mood_score, energy, stress, "
                "cycle_day, cycle_bleeding_level::text AS cycle_bleeding_level, "
                "sleep_minutes, sleep_quality, work_context::text AS work_context, "
                "note_visibility FROM entries WHERE id = :entry_id AND user_id = :user_id"
            ),
            {"entry_id": entry_id, "user_id": user_id},
        )
        .mappings()
        .one()
    )
    tag_ids = (
        conn.execute(
            sa.text(
                "SELECT tag_id FROM entry_tags WHERE entry_id = :entry_id "
                "AND user_id = :user_id ORDER BY tag_id"
            ),
            {"entry_id": entry_id, "user_id": user_id},
        )
        .scalars()
        .all()
    )
    symptoms = conn.execute(
        sa.text(
            "SELECT symptom_id, intensity FROM entry_symptoms WHERE entry_id = :entry_id "
            "AND user_id = :user_id"
        ),
        {"entry_id": entry_id, "user_id": user_id},
    ).all()
    payload: dict[str, object] = dict(entry)
    payload["entry_date"] = entry["entry_date"].isoformat()
    payload["note"] = None  # revision log never stores plaintext notes
    payload["tag_ids"] = [str(tag_id) for tag_id in tag_ids]
    payload["symptoms"] = {str(symptom_id): intensity for symptom_id, intensity in symptoms}
    _revision(conn, user_id, "entry", entry_id, payload, updated_at)


def _prepare_owner_rls_access(conn: Connection) -> tuple[str, ...]:
    """Temporarily let the schema owner run the cross-user backfill.

    PostgreSQL table owners normally bypass RLS, but CorrelCore deliberately
    uses ``FORCE ROW LEVEL SECURITY``.  A dedicated migration owner can safely
    suspend FORCE for this transaction; RLS remains enabled and the ALTERs are
    rolled back together with revision 049 if anything fails.
    """
    privileged = conn.execute(
        sa.text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user")
    ).scalar_one()
    if privileged:
        return ()

    table_names = ", ".join(f"'{name}'" for name in _RLS_TABLES)
    rows = conn.execute(
        sa.text(
            "SELECT c.relname, c.relowner = current_user::regrole AS owned, "
            "c.relforcerowsecurity FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            f"WHERE n.nspname = current_schema() AND c.relname IN ({table_names})"
        )
    ).all()
    by_name = {row.relname: row for row in rows}
    missing_or_foreign = [
        name for name in _RLS_TABLES if name not in by_name or not by_name[name].owned
    ]
    if missing_or_foreign:
        raise RuntimeError(
            "049 requires a superuser, BYPASSRLS role, or the owner of every backfill table; "
            f"not owned: {', '.join(missing_or_foreign)}"
        )

    forced = tuple(name for name in _RLS_TABLES if by_name[name].relforcerowsecurity)
    for name in forced:
        conn.execute(sa.text(f"ALTER TABLE {name} NO FORCE ROW LEVEL SECURITY"))
    return forced


def _restore_forced_rls(conn: Connection, tables: tuple[str, ...]) -> None:
    for name in tables:
        conn.execute(sa.text(f"ALTER TABLE {name} FORCE ROW LEVEL SECURITY"))


def _run_backfill(conn: Connection) -> None:
    """Convert all 049-era marker rows on Alembic's connection and transaction."""

    inconsistent = conn.execute(
        sa.text(
            "SELECT count(*) FROM entry_note_markers m JOIN entries e ON e.id = m.entry_id "
            "WHERE m.user_id <> e.user_id"
        )
    ).scalar_one()
    if inconsistent:
        raise RuntimeError("049: marker ownership differs from entry ownership")

    rows = conn.execute(
        sa.text(
            "SELECT m.user_id, m.entry_id, m.marker, e.note_visibility "
            "FROM entry_note_markers m JOIN entries e ON e.id = m.entry_id "
            "ORDER BY m.user_id, m.entry_id, m.marker"
        )
    ).all()
    default_slugs = set(
        conn.execute(sa.text("SELECT slug FROM tags WHERE is_default = true")).scalars()
    )
    claimed_by_user: dict[uuid.UUID, dict[str, str]] = defaultdict(dict)
    slugs_by_user: dict[uuid.UUID, dict[str, str]] = defaultdict(dict)
    # Reserve slugs before applying the per-entry cap. The legacy service did
    # this even when a full entry could not create a tag. Preserve its order
    # so a partially completed CLI run resumes without duplicate custom tags.
    for user_id, _entry_id, marker, visibility in rows:
        if visibility == "hidden" or marker in _OVERLAP or marker in _ONE_TO_ONE:
            continue
        if marker in slugs_by_user[user_id]:
            continue
        base = _slug(marker)
        if base is not None:
            slugs_by_user[user_id][marker] = _unique_slug(
                base, marker, default_slugs, claimed_by_user[user_id]
            )
    current_entry: tuple[uuid.UUID, uuid.UUID] | None = None
    current_tags: set[uuid.UUID] = set()
    touched_entries: set[tuple[uuid.UUID, uuid.UUID]] = set()
    links_added = tags_created = skipped = 0

    for user_id, entry_id, marker, visibility in rows:
        if visibility == "hidden":
            skipped += 1
            continue
        key = (user_id, entry_id)
        if current_entry != key:
            current_entry = key
            current_tags = set(
                conn.execute(
                    sa.text(
                        "SELECT tag_id FROM entry_tags WHERE entry_id = :entry_id "
                        "AND user_id = :user_id"
                    ),
                    {"entry_id": entry_id, "user_id": user_id},
                ).scalars()
            )
        if marker in _OVERLAP or _slug(marker) is None and marker not in _ONE_TO_ONE:
            skipped += 1
            continue
        # Resolve existing targets before the cap check so an already-linked
        # marker is a no-op. Creation is deferred until a slot is available.
        if len(current_tags) >= _MAX_TAGS_PER_ENTRY:
            skipped += 1
            continue
        tag_id, created = _tag_for_marker(
            conn,
            user_id,
            marker,
            default_slugs,
            claimed_by_user[user_id],
            slugs_by_user[user_id],
        )
        if tag_id is None:
            skipped += 1
            continue
        if tag_id in current_tags:
            continue
        result = conn.execute(
            sa.text(
                "INSERT INTO entry_tags (entry_id, tag_id, user_id) "
                "VALUES (:entry_id, :tag_id, :user_id) "
                "ON CONFLICT (entry_id, tag_id) DO NOTHING"
            ),
            {"entry_id": entry_id, "tag_id": tag_id, "user_id": user_id},
        )
        if result.rowcount != 1:
            continue
        current_tags.add(tag_id)
        links_added += 1
        tags_created += int(created)

        touched_entries.add((user_id, entry_id))

    for user_id, entry_id in sorted(touched_entries, key=lambda item: (str(item[0]), str(item[1]))):
        _entry_revision(conn, user_id, entry_id)

    logger.info(
        "049: converted %s marker links on %s entries; created %s tags; skipped %s markers",
        links_added,
        len(touched_entries),
        tags_created,
        skipped,
    )


def run(conn: Connection) -> None:
    """Run the backfill as a privileged role or the configured schema owner."""
    temporarily_unforced = _prepare_owner_rls_access(conn)
    _run_backfill(conn)
    _restore_forced_rls(conn, temporarily_unforced)
