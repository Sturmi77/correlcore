"""034 home_sections preference

Revision ID: 034
Revises: 033
Create Date: 2026-07-31

Configurable Home screen section order and visibility (#584). NULL means use
the server default brief-first layout; no backfill required for existing users.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "034"
down_revision: str | None = "033"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column("home_sections", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "home_sections")
