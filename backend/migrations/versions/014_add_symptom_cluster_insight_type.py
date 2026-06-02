"""014 add symptom cluster insight type

Revision ID: 014
Revises: 013
Create Date: 2026-05-31
"""

from __future__ import annotations

from alembic import op

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE insight_type ADD VALUE IF NOT EXISTS 'symptom_cluster'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed without recreating the type.
    # Keeping the additive value is data-safe for downgraded environments.
    pass
