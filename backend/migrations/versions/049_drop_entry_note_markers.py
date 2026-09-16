"""049 drop entry_note_markers (#903 C)

Revision ID: 049
Revises: 048
Create Date: 2026-09-16

Marker endgame after #890 Option 4: historical note markers were converted
to tags via the service-layer backfill (#895 / #900 / #901). The capture UI
and analytics were already removed (#896 / #897). This drops the leftover
``entry_note_markers`` table (and its RLS policies/indexes).

DSGVO note: ``export_service`` never included markers — only tags/notes —
so after a completed backfill the ZIP already reflects marker context as
tags. Unconverted marker-only rows would be irreversibly lost; run the
backfill before deploying this migration.

``InsightType.note_marker_mood`` rows are deleted here so the Python enum
member can be removed; the PostgreSQL enum label is left in place (PG
cannot DROP VALUE cleanly).

Tag blast radius
----------------
This migration does **not** write ``tags`` or ``entry_tags``. It only:

- deletes leftover ``insights`` rows with ``insight_type = 'note_marker_mood'``
  (tag correlation, symptom↔tag co-occurrence, and every other insight
  family stay);
- drops ``entry_note_markers`` (FKs point *from* markers *to* entries/users,
  so the drop cannot cascade into tags);
- leaves ``entry_note_signals`` in place.

The already-applied #895 backfill was add-only (``ON CONFLICT DO NOTHING``
on ``entry_tags``). It never updated or deleted tag rows. Converted
predefined markers were only the 1:1 catalogue slugs in
``CONVERTED_PREDEFINED_MARKERS``. Overlap keys in
``SKIPPED_OVERLAP_MARKERS`` were skipped so they could not land on
unrelated tags or fields (``work_intense``, ``good_sleep``, sport tags,
SymptomChecker, sliders, ``work_context``). Custom markers became new
per-user tags (or reused an existing *custom* tag of the same slug);
curated defaults were never mutated.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "049"
down_revision: str | None = "048"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

# Review lock: historical #895 backfill mapping. 049 itself never writes
# tags; these sets document which tags that conversion was allowed to
# *link* so a later reader can reconfirm the blast radius.
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


def upgrade() -> None:
    # Intentionally no writes to tags / entry_tags / entry_note_signals.
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
