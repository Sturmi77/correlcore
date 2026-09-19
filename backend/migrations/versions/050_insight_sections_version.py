"""050 insight_sections_version for Phase 6 hub shrink

Revision ID: 050
Revises: 049
Create Date: 2026-09-19

Versioned insight_sections layout (D5 / ADR-0043). Existing rows start at
version 1 (legacy all-on defaults). New rows default to version 2 (slim hub).
The v1→v2 transform runs lazily in the preferences service — no bulk JSON
rewrite here (FORCE RLS on user_preferences).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "050"
down_revision: str | None = "049"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "insight_sections_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    # New preference rows created after this revision start on the slim layout.
    op.alter_column(
        "user_preferences",
        "insight_sections_version",
        server_default=sa.text("2"),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "insight_sections_version")
