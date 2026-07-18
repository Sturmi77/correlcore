"""030 device_tokens for FCM / UnifiedPush registration (M11 Sprint 5)

Revision ID: 030
Revises: 029
Create Date: 2026-07-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "030"
down_revision: str | None = "029"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_TABLE = "device_tokens"


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
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("device_label", sa.Text(), nullable=True),
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
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("token", name="uq_device_tokens_token"),
        sa.CheckConstraint(
            "provider IN ('fcm', 'unifiedpush')",
            name="ck_device_tokens_provider",
        ),
        sa.CheckConstraint(
            "platform IN ('android', 'ios', 'web')",
            name="ck_device_tokens_platform",
        ),
    )
    op.create_index("ix_device_tokens_user_id", _TABLE, ["user_id"])

    op.execute(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY device_tokens_owner_select ON {_TABLE}
        FOR SELECT
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        f"""
        CREATE POLICY device_tokens_owner_insert ON {_TABLE}
        FOR INSERT
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        f"""
        CREATE POLICY device_tokens_owner_update ON {_TABLE}
        FOR UPDATE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        f"""
        CREATE POLICY device_tokens_owner_delete ON {_TABLE}
        FOR DELETE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    for pol in (
        "device_tokens_owner_delete",
        "device_tokens_owner_update",
        "device_tokens_owner_insert",
        "device_tokens_owner_select",
    ):
        op.execute(f"DROP POLICY IF EXISTS {pol} ON {_TABLE}")
    op.execute(f"ALTER TABLE {_TABLE} DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_device_tokens_user_id", table_name=_TABLE)
    op.drop_table(_TABLE)
