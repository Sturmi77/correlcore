"""018 add sync engine infrastructure for M4.1

Revision ID: 018
Revises: 017
Create Date: 2026-06-30

Stores per-user revision counters, pull deltas, push idempotency keys, and
client sequence checkpoints required by ADR-0036 §3–§4.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_SYNC_TABLES = (
    "sync_user_revisions",
    "sync_revision_log",
    "sync_push_batches",
    "sync_client_state",
)


def upgrade() -> None:
    op.create_table(
        "sync_user_revisions",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "current_rev",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "sync_revision_log",
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
        sa.Column("user_rev", sa.BigInteger(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("entity_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "entity_type IN ('entry', 'tag', 'symptom')",
            name="ck_sync_revision_log_entity_type",
        ),
        sa.CheckConstraint(
            "operation IN ('upsert', 'delete')",
            name="ck_sync_revision_log_operation",
        ),
        sa.UniqueConstraint("user_id", "user_rev", name="uq_sync_revision_log_user_rev"),
    )
    op.create_index(
        "ix_sync_revision_log_user_rev",
        "sync_revision_log",
        ["user_id", "user_rev"],
    )
    op.create_index(
        "ix_sync_revision_log_user_created_at",
        "sync_revision_log",
        ["user_id", "created_at"],
    )

    op.create_table(
        "sync_push_batches",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cursor", sa.Text(), nullable=False),
        sa.Column("applied", sa.Integer(), nullable=False),
        sa.Column("skipped", sa.Integer(), nullable=False),
        sa.Column(
            "conflicts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("user_id", "client_id", "batch_id"),
    )

    op.create_table(
        "sync_client_state",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "last_applied_seq",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("user_id", "client_id"),
    )

    for table in _SYNC_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        for action in ("select", "insert", "update", "delete"):
            using = (
                "USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)"
                if action in ("select", "update", "delete")
                else ""
            )
            check = (
                "WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)"
                if action in ("insert", "update")
                else ""
            )
            clause = f"{using} {check}".strip()
            op.execute(
                f"""
                CREATE POLICY sync_{table}_owner_{action} ON {table}
                FOR {action.upper()}
                {clause}
                """
            )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'correlcore_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON sync_user_revisions TO correlcore_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON sync_revision_log TO correlcore_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON sync_push_batches TO correlcore_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON sync_client_state TO correlcore_app;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    for table in reversed(_SYNC_TABLES):
        for action in ("delete", "update", "insert", "select"):
            op.execute(f"DROP POLICY IF EXISTS sync_{table}_owner_{action} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("sync_client_state")
    op.drop_table("sync_push_batches")
    op.drop_index("ix_sync_revision_log_user_created_at", table_name="sync_revision_log")
    op.drop_index("ix_sync_revision_log_user_rev", table_name="sync_revision_log")
    op.drop_table("sync_revision_log")
    op.drop_table("sync_user_revisions")
