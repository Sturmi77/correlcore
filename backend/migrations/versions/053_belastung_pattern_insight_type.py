"""053 belastung_pattern insight type (Phase 8 / #875)

Revision ID: 053
Revises: 052
Create Date: 2026-09-19
"""

from __future__ import annotations

from alembic import op

revision: str = "053"
down_revision: str | None = "052"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE insight_type ADD VALUE IF NOT EXISTS 'belastung_pattern'")


def downgrade() -> None:
    pass
