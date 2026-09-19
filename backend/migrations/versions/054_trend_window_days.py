"""054 trend_window_days preference

Revision ID: 054
Revises: 053
Create Date: 2026-09-19

Server-side analysis window for Home / Trends / Insights (#867, Phase 2 of
the Insight Surface Layers rollout). Allowed values are 14 | 28 | 90 days;
default 28 matches the previous hardcoded TREND_WINDOW_DAYS constant.

Renumbered from 050 on merge into the Phase 6–8 stack (050–053 already taken).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "054"
down_revision: str | None = "053"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "trend_window_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("28"),
        ),
    )
    op.create_check_constraint(
        "ck_user_preferences_trend_window_days",
        "user_preferences",
        "trend_window_days IN (14, 28, 90)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_user_preferences_trend_window_days",
        "user_preferences",
        type_="check",
    )
    op.drop_column("user_preferences", "trend_window_days")
