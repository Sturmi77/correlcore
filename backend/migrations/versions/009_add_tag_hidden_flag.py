"""009 add hidden flag for user tag overrides

Revision ID: 009
Revises: 008
Create Date: 2026-05-10

Issue #124 lets users hide curated defaults for their own account. The
global default row stays unchanged; hiding is represented by a user-owned
copy-on-write tag with the same slug and ``is_hidden = TRUE``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "tags",
        sa.Column(
            "is_hidden",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tags", "is_hidden")
