"""051 null_association insight type (Phase 7 / D2)

Revision ID: 051
Revises: 050
Create Date: 2026-09-19

Non-result associations ("X changed nothing") share the G2 with/without
frame but must not enter the correlation matrix gate. Additive PG enum
value; cannot be dropped cleanly on downgrade.
"""

from __future__ import annotations

from alembic import op

revision: str = "051"
down_revision: str | None = "050"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE insight_type ADD VALUE IF NOT EXISTS 'null_association'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed without recreating the type.
    pass
