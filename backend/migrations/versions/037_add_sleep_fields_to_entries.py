"""037 sleep_minutes / sleep_quality on entries

Revision ID: 037
Revises: 036
Create Date: 2026-08-02

M8 Sprint 1 (#172): optional manual sleep tracking per entry.
- ``sleep_minutes``: total sleep duration, 0..1440 (24h).
- ``sleep_quality``: subjective quality 1..5 (same scale family as mood).
Both nullable; existing rows keep NULL. Health Connect import (M8 S2) later
writes these with ``source = wearable`` — manual values always win.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "037"
down_revision: str | None = "036"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column("entries", sa.Column("sleep_minutes", sa.Integer(), nullable=True))
    op.add_column("entries", sa.Column("sleep_quality", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_entries_sleep_minutes_range",
        "entries",
        "sleep_minutes IS NULL OR sleep_minutes BETWEEN 0 AND 1440",
    )
    op.create_check_constraint(
        "ck_entries_sleep_quality_range",
        "entries",
        "sleep_quality IS NULL OR sleep_quality BETWEEN 1 AND 5",
    )


def downgrade() -> None:
    op.drop_constraint("ck_entries_sleep_quality_range", "entries", type_="check")
    op.drop_constraint("ck_entries_sleep_minutes_range", "entries", type_="check")
    op.drop_column("entries", "sleep_quality")
    op.drop_column("entries", "sleep_minutes")
