"""015 add symptom analytics insight types

Revision ID: 015
Revises: 014
Create Date: 2026-05-31
"""

from __future__ import annotations

from alembic import op

revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE insight_type ADD VALUE IF NOT EXISTS 'symptom_mood_association'")
    op.execute("ALTER TYPE insight_type ADD VALUE IF NOT EXISTS 'symptom_tag_cooccurrence'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed without recreating the type.
    # Keeping additive values is data-safe for downgraded environments.
    pass
