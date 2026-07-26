"""032 cycle_tracking_enabled preference

Revision ID: 032
Revises: 031
Create Date: 2026-07-26

Opt-out toggle for the cycle-day tracking function (ADR-0034, Stage 1). Set in
the last onboarding screen and re-toggleable in Settings. Existing users default
to enabled so no already-onboarded user loses the cycle-day field on deploy.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "032"
down_revision: str | None = "031"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "cycle_tracking_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "cycle_tracking_enabled")
