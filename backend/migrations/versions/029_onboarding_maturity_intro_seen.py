"""029 onboarding_maturity_intro_seen preference

Revision ID: 029
Revises: 028
Create Date: 2026-07-18

One-time Home sheet after the first entry that explains insight maturity
phases 1–4. Existing onboarded users are marked seen so they are not
interrupted on deploy.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "029"
down_revision: str | None = "028"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "onboarding_maturity_intro_seen",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE user_preferences
            SET onboarding_maturity_intro_seen = true
            WHERE onboarding_retro_completed = true
            """
        )
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "onboarding_maturity_intro_seen")
