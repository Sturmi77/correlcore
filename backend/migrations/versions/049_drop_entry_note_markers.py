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
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "049"
down_revision: str | None = "048"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
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
