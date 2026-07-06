"""020 add calendar context insight types

Revision ID: 020
Revises: 019
Create Date: 2026-07-05
"""

from __future__ import annotations

from alembic import op

revision: str = "020"
down_revision: str | None = "019"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE insight_type ADD VALUE IF NOT EXISTS 'work_context_pattern'")
    op.execute("ALTER TYPE insight_type ADD VALUE IF NOT EXISTS 'weekday_context_pattern'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed without recreating the type.
    # Keeping additive values is data-safe for downgraded environments.
    pass
