"""017 add sync_conflicts table for M4.1 offline sync

Revision ID: 017
Revises: 016
Create Date: 2026-06-30

Stores field-level LWW conflict metadata per ADR-0003 / ADR-0036. The merge
write path lands in Sprint 2; this migration creates storage + RLS only.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "017"
down_revision: str | None = "016"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_ENTITY_TYPES = ("entry", "tag", "symptom")


def upgrade() -> None:
    op.create_table(
        "sync_conflicts",
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
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column(
            "client_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "server_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("client_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("server_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            f"entity_type IN ({', '.join(repr(v) for v in _ENTITY_TYPES)})",
            name="ck_sync_conflicts_entity_type",
        ),
    )
    op.create_index(
        "ix_sync_conflicts_user_created_at",
        "sync_conflicts",
        ["user_id", "created_at"],
    )
    op.create_index("ix_sync_conflicts_entity_id", "sync_conflicts", ["entity_id"])

    op.execute("ALTER TABLE sync_conflicts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sync_conflicts FORCE ROW LEVEL SECURITY")
    for policy in (
        """
        CREATE POLICY sync_conflicts_owner_select ON sync_conflicts
        FOR SELECT
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """,
        """
        CREATE POLICY sync_conflicts_owner_insert ON sync_conflicts
        FOR INSERT
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """,
        """
        CREATE POLICY sync_conflicts_owner_update ON sync_conflicts
        FOR UPDATE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """,
        """
        CREATE POLICY sync_conflicts_owner_delete ON sync_conflicts
        FOR DELETE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """,
    ):
        op.execute(policy)

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'correlcore_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON sync_conflicts TO correlcore_app;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    for policy in (
        "sync_conflicts_owner_delete",
        "sync_conflicts_owner_update",
        "sync_conflicts_owner_insert",
        "sync_conflicts_owner_select",
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON sync_conflicts")

    op.execute("ALTER TABLE sync_conflicts NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sync_conflicts DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_sync_conflicts_entity_id", table_name="sync_conflicts")
    op.drop_index("ix_sync_conflicts_user_created_at", table_name="sync_conflicts")
    op.drop_table("sync_conflicts")
