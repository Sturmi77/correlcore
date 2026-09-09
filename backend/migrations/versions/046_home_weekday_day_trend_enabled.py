"""046 home_weekday_day_trend_enabled preference

Revision ID: 046
Revises: 045
Create Date: 2026-09-09

Opt-out toggle for the per-weekday (W2) trend caret on Home (#868). Default
true so existing users see the indicator; it can be noisy at N=28 (~4 values
per weekday) so Settings can hide it. The aggregate W1 badge is unaffected.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "046"
down_revision: str | None = "045"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "home_weekday_day_trend_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "home_weekday_day_trend_enabled")
