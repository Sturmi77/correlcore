"""025 consent_log for DSGVO Art. 9 explicit consent (Issue #31)

Revision ID: 025
Revises: 024
Create Date: 2026-07-15

Append-only audit log for user consents (e.g. Health Connect import).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "025"
down_revision: str | None = "024"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_TABLE = "consent_log"


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
        sa.Column("consent_type", sa.Text(), nullable=False),
        sa.Column("consent_version", sa.Text(), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_consent_log_user_id", _TABLE, ["user_id"])
    op.create_index(
        "idx_consent_log_user_type_created",
        _TABLE,
        ["user_id", "consent_type", "created_at"],
    )

    op.execute(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY consent_log_owner_select ON {_TABLE}
        FOR SELECT
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        f"""
        CREATE POLICY consent_log_owner_insert ON {_TABLE}
        FOR INSERT
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        f"""
        CREATE POLICY consent_log_owner_update ON {_TABLE}
        FOR UPDATE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        f"""
        CREATE POLICY consent_log_owner_delete ON {_TABLE}
        FOR DELETE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    for pol in (
        "consent_log_owner_delete",
        "consent_log_owner_update",
        "consent_log_owner_insert",
        "consent_log_owner_select",
    ):
        op.execute(f"DROP POLICY IF EXISTS {pol} ON {_TABLE}")
    op.execute(f"ALTER TABLE {_TABLE} DISABLE ROW LEVEL SECURITY")
    op.drop_index("idx_consent_log_user_type_created", table_name=_TABLE)
    op.drop_index("ix_consent_log_user_id", table_name=_TABLE)
    op.drop_table(_TABLE)
