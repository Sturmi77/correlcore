"""049 drop entry_note_markers (#903 C)

Revision ID: 049
Revises: 048
Create Date: 2026-09-16

Marker endgame after #890 Option 4. Before dropping ``entry_note_markers``,
``upgrade()`` converts retained markers on Alembic's own connection. That keeps
the conversion in the same transaction as revision 048's DDL and the DROP;
no child process can block on locks held by its waiting parent.
The backfill is add-only: it only inserts missing ``entry_tags`` links for
marker-derived tags (predefined 1:1 map + custom markers) and never deletes,
renames, or rewrites unrelated tags.

After a successful backfill, this migration deletes leftover
``note_marker_mood`` insight rows and drops the markers table. The PostgreSQL
``insight_type`` enum label is left in place (PG cannot DROP VALUE cleanly).

Tag blast radius
----------------
The Alembic DDL in this file does not write ``tags`` / ``entry_tags`` /
``entry_note_signals``. It only:

- runs the add-only backfill on the migration connection — may insert missing ``entry_tags``
  for marker-derived targets only;
- deletes leftover ``insights`` rows with ``insight_type = 'note_marker_mood'``
  (tag correlation, symptom↔tag co-occurrence, and every other insight
  family stay);
- drops ``entry_note_markers`` (FKs point *from* markers *to* entries/users,
  so the drop cannot cascade into tags);
- leaves ``entry_note_signals`` in place.

Converted predefined markers are only the 1:1 catalogue slugs in
``CONVERTED_PREDEFINED_MARKERS``. Overlap keys in ``SKIPPED_OVERLAP_MARKERS``
are skipped so they cannot land on unrelated tags or fields
(``work_intense``, ``good_sleep``, sport tags, SymptomChecker, sliders,
``work_context``). Custom markers become new per-user tags (or reuse an
existing *custom* tag of the same slug); curated defaults are never mutated.
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op

from migrations.marker_tag_backfill_049 import run as backfill_on_migration_connection

revision: str = "049"
down_revision: str | None = "048"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

logger = logging.getLogger("alembic.runtime.migration")

# Review lock: historical #895 backfill mapping — which tags conversion may
# *link* (never rewrite). Overlap keys stay unmapped.
CONVERTED_PREDEFINED_MARKERS: frozenset[str] = frozenset({"conflict", "travel", "achievement"})
SKIPPED_OVERLAP_MARKERS: frozenset[str] = frozenset(
    {
        "work",
        "homeoffice",
        "social",
        "movement",
        "sleep_bad",
        "sleep_good",
        "stress",
        "symptom",
    }
)


def _run_marker_tag_backfill() -> None:
    """Convert remaining markers in the caller's open Alembic transaction."""
    logger.info("049: converting markers on the migration connection before DROP TABLE")
    backfill_on_migration_connection(op.get_bind())


def upgrade() -> None:
    _run_marker_tag_backfill()

    op.execute("DELETE FROM insights WHERE insight_type = 'note_marker_mood'")

    for pol in (
        "entry_note_markers_owner_delete",
        "entry_note_markers_owner_update",
        "entry_note_markers_owner_insert",
        "entry_note_markers_owner_select",
    ):
        op.execute(f"DROP POLICY IF EXISTS {pol} ON entry_note_markers")
    op.execute("ALTER TABLE entry_note_markers DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_entry_note_markers_user_id", table_name="entry_note_markers")
    op.drop_index("idx_note_markers_entry", table_name="entry_note_markers")
    op.drop_table("entry_note_markers")


def downgrade() -> None:
    op.create_table(
        "entry_note_markers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entry_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("marker", sa.Text(), nullable=False),
        sa.Column(
            "source",
            sa.Text(),
            nullable=False,
            server_default="user",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["entry_id"], ["entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entry_id", "marker", name="uq_entry_note_markers_entry_marker"),
        sa.CheckConstraint(
            "source IN ('user', 'suggestion')",
            name="ck_entry_note_markers_source_allowed",
        ),
    )
    op.create_index("idx_note_markers_entry", "entry_note_markers", ["entry_id"])
    op.create_index("ix_entry_note_markers_user_id", "entry_note_markers", ["user_id"])

    op.execute("ALTER TABLE entry_note_markers ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY entry_note_markers_owner_select ON entry_note_markers
        FOR SELECT
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY entry_note_markers_owner_insert ON entry_note_markers
        FOR INSERT
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY entry_note_markers_owner_update ON entry_note_markers
        FOR UPDATE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY entry_note_markers_owner_delete ON entry_note_markers
        FOR DELETE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
