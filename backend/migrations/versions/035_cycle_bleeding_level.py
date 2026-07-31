"""035 cycle_bleeding_level on entries

Revision ID: 035
Revises: 034
Create Date: 2026-07-31

Stage 1 cycle tracking (#547): optional bleeding strength per entry (SHD).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "035"
down_revision: str | None = "034"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

BLEEDING_LEVEL = sa.Enum(
    "none",
    "spotting",
    "light",
    "medium",
    "heavy",
    name="bleeding_level",
    create_type=True,
)


def upgrade() -> None:
    BLEEDING_LEVEL.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "entries",
        sa.Column("cycle_bleeding_level", BLEEDING_LEVEL, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("entries", "cycle_bleeding_level")
    BLEEDING_LEVEL.drop(op.get_bind(), checkfirst=True)
