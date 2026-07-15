"""026 weekly digest preference, changepoint insight type, digest snapshots

Revision ID: 026
Revises: 025
Create Date: 2026-07-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "026"
down_revision: str | None = "025"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "digest_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.execute("ALTER TYPE insight_type ADD VALUE IF NOT EXISTS 'changepoint'")
    op.execute("ALTER TYPE worker_job_kind ADD VALUE IF NOT EXISTS 'digest'")

    op.create_table(
        "insight_digests",
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
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column(
            "insight_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("insight_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("push_title", sa.Text(), nullable=False),
        sa.Column("push_body", sa.Text(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_insight_digests_user_generated_at",
        "insight_digests",
        ["user_id", "generated_at"],
    )

    # Separate executes — asyncpg rejects multi-statement prepared SQL.
    op.execute("ALTER TABLE insight_digests ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE insight_digests FORCE ROW LEVEL SECURITY")
    for policy in ("select", "insert", "update", "delete"):
        using = "user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid"
        if policy in {"select", "update", "delete"}:
            op.execute(
                f"""
                CREATE POLICY insight_digests_owner_{policy} ON insight_digests
                FOR {policy.upper()}
                USING ({using})
                """
                + (f" WITH CHECK ({using})" if policy == "update" else "")
            )
        else:
            op.execute(
                f"""
                CREATE POLICY insight_digests_owner_{policy} ON insight_digests
                FOR INSERT
                WITH CHECK ({using})
                """
            )


def downgrade() -> None:
    for policy in ("delete", "update", "insert", "select"):
        op.execute(f"DROP POLICY IF EXISTS insight_digests_owner_{policy} ON insight_digests")
    op.execute("ALTER TABLE insight_digests NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE insight_digests DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_insight_digests_user_generated_at", table_name="insight_digests")
    op.drop_table("insight_digests")
    op.drop_column("user_preferences", "digest_enabled")
    # PostgreSQL enum values cannot be removed without recreating the type.
