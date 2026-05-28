"""013 add cycle day to entries

Revision ID: 013
Revises: 012
Create Date: 2026-05-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE tag_category ADD VALUE IF NOT EXISTS 'cycle'")
    op.add_column("entries", sa.Column("cycle_day", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_entries_cycle_day_range",
        "entries",
        "cycle_day IS NULL OR cycle_day BETWEEN 1 AND 35",
    )


def downgrade() -> None:
    op.drop_constraint("ck_entries_cycle_day_range", "entries", type_="check")
    op.drop_column("entries", "cycle_day")
    # PostgreSQL enum values cannot be removed without recreating the type.
    # Leaving the additive value in place keeps downgrade data-safe.
