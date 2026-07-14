"""022 add include_in_analytics flag for tags

Revision ID: 022
Revises: 021
Create Date: 2026-07-14

Lets users keep tracking a tag (including habits such as medication)
while excluding it from insight generation, heatmaps, co-occurrence and
tag clusters. Habit adherence stats are unaffected.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "022"
down_revision: str | None = "021"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "tags",
        sa.Column(
            "include_in_analytics",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tags", "include_in_analytics")
