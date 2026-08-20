"""042 last_seen_digest_at preference

Revision ID: 042
Revises: 041
Create Date: 2026-08-20

#739: tracks the newest weekly digest a user has already seen in the one-time
in-app modal. Nullable timestamptz; NULL means the modal has never been shown,
so the first stored digest triggers it. Mirrors ``last_seen_insight_at``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "042"
down_revision: str | None = "041"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column("last_seen_digest_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "last_seen_digest_at")
