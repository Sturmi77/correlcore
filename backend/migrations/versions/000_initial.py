"""000 initial placeholder

Revision ID: 000
Revises:
Create Date: 2026-04-28

This is an empty baseline migration — it marks the starting point
of the migration chain. All actual schema changes start from 001.
"""

from __future__ import annotations

revision: str = "000"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
