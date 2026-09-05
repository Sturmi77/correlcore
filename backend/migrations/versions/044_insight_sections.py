"""044 insight_sections preference

Revision ID: 044
Revises: 043
Create Date: 2026-09-05

Configurable Insights page section order and visibility (#821). NULL means use
the server default layout; no backfill required for existing users.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "044"
down_revision: str | None = "043"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column("insight_sections", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "insight_sections")
