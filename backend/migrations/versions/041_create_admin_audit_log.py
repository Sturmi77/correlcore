"""041 create admin_audit_log (#677 admin console P2)

Revision ID: 041
Revises: 040
Create Date: 2026-08-14

Append-only audit of sensitive admin actions (delete/disable/enable/reset).
No FK to ``users`` on actor or target: the target column must survive the
deletion it records, and the trail must outlive an actor removed later. Emails
are stored for readability once the rows are gone.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "041"
down_revision: str | None = "040"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_TABLE = "admin_audit_log"


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
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_email", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_email", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_admin_audit_log_actor_user_id", _TABLE, ["actor_user_id"])
    op.create_index("ix_admin_audit_log_target_user_id", _TABLE, ["target_user_id"])
    op.create_index("ix_admin_audit_log_created_at", _TABLE, ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_admin_audit_log_created_at", table_name=_TABLE)
    op.drop_index("ix_admin_audit_log_target_user_id", table_name=_TABLE)
    op.drop_index("ix_admin_audit_log_actor_user_id", table_name=_TABLE)
    op.drop_table(_TABLE)
