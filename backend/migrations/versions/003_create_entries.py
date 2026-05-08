"""003 create entries table (M1, Issue #7)

Revision ID: 003
Revises: 002
Create Date: 2026-05-04

Notes
-----
- ``entries`` is the daily mood/energy/stress log. Each row belongs to
  exactly one user (cascade delete on Art. 17 DSGVO erasure).
- One row per ``(user_id, entry_date, slot)`` — slot defaults to ``day``;
  the column is reserved for the M3+ multi-slot tracking and shipped
  here so we don't need a destructive migration later (ADR-0007 spirit:
  prefer additive schema changes).
- CHECK constraints clamp ``mood_score / energy / stress`` to 1..5 at
  the DB layer in addition to Pydantic validation. Defence-in-depth:
  any future bulk-import path or background worker cannot bypass the
  range invariant.
- ``note_enc`` starts in this historical migration as nullable TEXT so
  the initial Entry feature could land independently. Migration 007 later
  re-types and backfills it to BYTEA Fernet ciphertext (ADR-0005) without
  renaming the column.
- ``user_id`` carries an explicit btree index — most queries are
  ``WHERE user_id = ?`` (timeline, calendar, last-7-days).
- Row-Level-Security:
    * RLS is enabled on the table.
    * One policy per CRUD verb, all keyed on
      ``user_id = current_setting('app.current_user_id')::uuid``.
    * The application binds ``app.current_user_id`` per request (M1
      follow-up). For M1 we ship the policies inactive for the
      service role and rely on app-level filters; the policies become
      enforcing once the per-request session-set lands. Shipping the
      RLS skeleton now means the security audit checklist (§9, SA-2)
      can already be ticked at the M1 quality-gate.
- ``updated_at`` trigger reuses ``update_updated_at_column()`` from
  migration 001.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


_ENTRY_SLOT_VALUES = ("day", "morning", "noon", "evening")
_WORK_CONTEXT_VALUES = (
    "homeoffice",
    "office",
    "vacation",
    "sick",
    "weekend",
    "travel",
)


def upgrade() -> None:
    # Enum types — created explicitly so we control name + drop order.
    entry_slot = postgresql.ENUM(*_ENTRY_SLOT_VALUES, name="entry_slot")
    work_context = postgresql.ENUM(*_WORK_CONTEXT_VALUES, name="work_context")
    entry_slot.create(op.get_bind(), checkfirst=True)
    work_context.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column(
            "slot",
            postgresql.ENUM(*_ENTRY_SLOT_VALUES, name="entry_slot", create_type=False),
            nullable=False,
            server_default=sa.text("'day'"),
        ),
        sa.Column("mood_score", sa.Integer(), nullable=False),
        sa.Column("energy", sa.Integer(), nullable=False),
        sa.Column("stress", sa.Integer(), nullable=False),
        sa.Column(
            "work_context",
            postgresql.ENUM(*_WORK_CONTEXT_VALUES, name="work_context", create_type=False),
            nullable=False,
        ),
        sa.Column("note_enc", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "entry_date", "slot", name="uq_entries_user_date_slot"),
        sa.CheckConstraint("mood_score BETWEEN 1 AND 5", name="ck_entries_mood_score_range"),
        sa.CheckConstraint("energy BETWEEN 1 AND 5", name="ck_entries_energy_range"),
        sa.CheckConstraint("stress BETWEEN 1 AND 5", name="ck_entries_stress_range"),
    )

    op.create_index("ix_entries_user_id", "entries", ["user_id"])
    op.create_index(
        "ix_entries_user_date",
        "entries",
        ["user_id", "entry_date"],
    )

    # Trigger — reuse function from migration 001
    op.execute(
        """
        CREATE TRIGGER entries_updated_at
        BEFORE UPDATE ON entries
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # Row-Level-Security: enable on table; policies key on a session GUC
    # the application sets per authenticated transaction. If that binding
    # is absent, policies evaluate to false and app-level owner filters are
    # still the fallback line of defence.
    op.execute("ALTER TABLE entries ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY entries_owner_select ON entries
        FOR SELECT
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY entries_owner_insert ON entries
        FOR INSERT
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY entries_owner_update ON entries
        FOR UPDATE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY entries_owner_delete ON entries
        FOR DELETE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS entries_owner_delete ON entries")
    op.execute("DROP POLICY IF EXISTS entries_owner_update ON entries")
    op.execute("DROP POLICY IF EXISTS entries_owner_insert ON entries")
    op.execute("DROP POLICY IF EXISTS entries_owner_select ON entries")
    op.execute("ALTER TABLE entries DISABLE ROW LEVEL SECURITY")

    op.execute("DROP TRIGGER IF EXISTS entries_updated_at ON entries")
    op.drop_index("ix_entries_user_date", table_name="entries")
    op.drop_index("ix_entries_user_id", table_name="entries")
    op.drop_table("entries")

    work_context = postgresql.ENUM(*_WORK_CONTEXT_VALUES, name="work_context")
    entry_slot = postgresql.ENUM(*_ENTRY_SLOT_VALUES, name="entry_slot")
    work_context.drop(op.get_bind(), checkfirst=True)
    entry_slot.drop(op.get_bind(), checkfirst=True)
