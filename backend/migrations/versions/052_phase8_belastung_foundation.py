"""052 Phase 8: work_context.other, write-time covariates, belastung opt-in

Revision ID: 052
Revises: 051
Create Date: 2026-09-19

- Add ``other`` to ``work_context`` (#875 recovery labeling).
- Add nullable ``logged_local_hour`` / ``inferred_period`` on entries (#892
  Option 3). Derived from first local write; ``slot`` stays ``day``.
- Add ``belastung_overlay_enabled`` on user_preferences (default false).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "052"
down_revision: str | None = "051"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE work_context ADD VALUE IF NOT EXISTS 'other'")

    inferred_period = postgresql.ENUM(
        "morning",
        "daytime",
        "evening",
        "after_hours",
        name="inferred_period",
        create_type=False,
    )
    inferred_period.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "entries",
        sa.Column("logged_local_hour", sa.Integer(), nullable=True),
    )
    op.add_column(
        "entries",
        sa.Column(
            "inferred_period",
            postgresql.ENUM(
                "morning",
                "daytime",
                "evening",
                "after_hours",
                name="inferred_period",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_entries_logged_local_hour_range",
        "entries",
        "logged_local_hour IS NULL OR (logged_local_hour >= 0 AND logged_local_hour <= 23)",
    )

    op.add_column(
        "user_preferences",
        sa.Column(
            "belastung_overlay_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "belastung_overlay_enabled")
    op.drop_constraint("ck_entries_logged_local_hour_range", "entries", type_="check")
    op.drop_column("entries", "inferred_period")
    op.drop_column("entries", "logged_local_hour")
    op.execute("DROP TYPE IF EXISTS inferred_period")
    # work_context.other cannot be dropped cleanly from PG enums.
