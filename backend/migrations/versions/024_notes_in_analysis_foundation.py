"""024 notes in analysis foundation (Issues #195-#199)

Revision ID: 024
Revises: 023
Create Date: 2026-07-15

Extends ``entries`` with note preview/visibility metadata (``note_enc`` stays
the encrypted body per ADR-0005). Adds ``entry_note_markers`` and
``entry_note_signals`` for structured note analysis.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "024"
down_revision: str | None = "023"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_NOTE_VISIBILITY_VALUES = ("full", "analysis_only", "hidden")
_MARKER_SOURCE_VALUES = ("user", "suggestion")


def upgrade() -> None:
    op.add_column("entries", sa.Column("note_summary_short", sa.Text(), nullable=True))
    op.add_column(
        "entries",
        sa.Column(
            "note_visibility",
            sa.Text(),
            nullable=False,
            server_default="full",
        ),
    )
    op.add_column(
        "entries",
        sa.Column("note_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_entries_note_visibility_allowed",
        "entries",
        "note_visibility IN ('full', 'analysis_only', 'hidden')",
    )

    op.create_table(
        "entry_note_markers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
        sa.UniqueConstraint("entry_id", "marker", name="uq_entry_note_markers_entry_marker"),
        sa.CheckConstraint(
            "source IN ('user', 'suggestion')",
            name="ck_entry_note_markers_source_allowed",
        ),
    )
    op.create_index("idx_note_markers_entry", "entry_note_markers", ["entry_id"])
    op.create_index("ix_entry_note_markers_user_id", "entry_note_markers", ["user_id"])

    op.create_table(
        "entry_note_signals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("signal", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("source_span", sa.Text(), nullable=True),
        sa.Column("extractor_v", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_entry_note_signals_confidence_range",
        ),
    )
    op.create_index("idx_note_signals_entry", "entry_note_signals", ["entry_id"])
    op.create_index("idx_note_signals_signal", "entry_note_signals", ["signal"])
    op.create_index("ix_entry_note_signals_user_id", "entry_note_signals", ["user_id"])

    op.execute("ALTER TYPE insight_type ADD VALUE IF NOT EXISTS 'note_marker_mood'")

    for table in ("entry_note_markers", "entry_note_signals"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_owner_select ON {table}
            FOR SELECT
            USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
            """
        )
        op.execute(
            f"""
            CREATE POLICY {table}_owner_insert ON {table}
            FOR INSERT
            WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
            """
        )
        op.execute(
            f"""
            CREATE POLICY {table}_owner_update ON {table}
            FOR UPDATE
            USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
            WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
            """
        )
        op.execute(
            f"""
            CREATE POLICY {table}_owner_delete ON {table}
            FOR DELETE
            USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
            """
        )


def downgrade() -> None:
    for table in ("entry_note_signals", "entry_note_markers"):
        for pol in (
            f"{table}_owner_delete",
            f"{table}_owner_update",
            f"{table}_owner_insert",
            f"{table}_owner_select",
        ):
            op.execute(f"DROP POLICY IF EXISTS {pol} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_entry_note_signals_user_id", table_name="entry_note_signals")
    op.drop_index("idx_note_signals_signal", table_name="entry_note_signals")
    op.drop_index("idx_note_signals_entry", table_name="entry_note_signals")
    op.drop_table("entry_note_signals")

    op.drop_index("ix_entry_note_markers_user_id", table_name="entry_note_markers")
    op.drop_index("idx_note_markers_entry", table_name="entry_note_markers")
    op.drop_table("entry_note_markers")

    op.drop_constraint("ck_entries_note_visibility_allowed", "entries", type_="check")
    op.drop_column("entries", "note_updated_at")
    op.drop_column("entries", "note_visibility")
    op.drop_column("entries", "note_summary_short")
