"""008 add habit schema preview fields to tags (M2, ADR-0012)

Revision ID: 008
Revises: 007
Create Date: 2026-05-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "tags",
        sa.Column(
            "habit_type",
            sa.String(length=8),
            nullable=False,
            server_default=sa.text("'none'"),
        ),
    )
    op.add_column(
        "tags",
        sa.Column(
            "target_frequency",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_tags_habit_type_valid",
        "tags",
        "habit_type IN ('none', 'build', 'reduce')",
    )
    op.create_check_constraint(
        "ck_tags_target_frequency_consistent",
        "tags",
        "(habit_type = 'none' AND target_frequency IS NULL) "
        "OR (habit_type IN ('build', 'reduce') AND target_frequency BETWEEN 1 AND 7)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tags_target_frequency_consistent", "tags", type_="check")
    op.drop_constraint("ck_tags_habit_type_valid", "tags", type_="check")
    op.drop_column("tags", "target_frequency")
    op.drop_column("tags", "habit_type")
