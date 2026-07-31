"""034 create insight_dismissals for subject-stable hide (#601 Phase 1)

Revision ID: 034
Revises: 033
Create Date: 2026-07-31
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "034"
down_revision: str | None = "033"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_TABLE = "insight_dismissals"


def upgrade() -> None:
    op.create_table(
        _TABLE,
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
        sa.Column("subject_key", sa.String(length=1024), nullable=False),
        sa.Column(
            "insight_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("insights.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "subject_key", name="uq_insight_dismissals_user_subject"),
    )
    op.create_index("ix_insight_dismissals_user_id", _TABLE, ["user_id"])
    op.create_index(
        "ix_insight_dismissals_user_dismissed_at",
        _TABLE,
        ["user_id", "dismissed_at"],
    )

    op.execute(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY insight_dismissals_owner_select ON {_TABLE}
        FOR SELECT
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        f"""
        CREATE POLICY insight_dismissals_owner_insert ON {_TABLE}
        FOR INSERT
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        f"""
        CREATE POLICY insight_dismissals_owner_update ON {_TABLE}
        FOR UPDATE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        f"""
        CREATE POLICY insight_dismissals_owner_delete ON {_TABLE}
        FOR DELETE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'correlcore_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON {_TABLE} TO correlcore_app;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    for pol in (
        "insight_dismissals_owner_delete",
        "insight_dismissals_owner_update",
        "insight_dismissals_owner_insert",
        "insight_dismissals_owner_select",
    ):
        op.execute(f"DROP POLICY IF EXISTS {pol} ON {_TABLE}")
    op.execute(f"ALTER TABLE {_TABLE} DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_insight_dismissals_user_dismissed_at", table_name=_TABLE)
    op.drop_index("ix_insight_dismissals_user_id", table_name=_TABLE)
    op.drop_table(_TABLE)
