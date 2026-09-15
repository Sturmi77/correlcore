"""048 add tags.is_pinned

Revision ID: 048
Revises: 047
Create Date: 2026-09-14

User-pinned favourite tags (#903 A). Pinned tags are surfaced first in the
entry-form "recently used" cloud regardless of the recency window, so a
rare-but-important tag never falls off. Additive boolean, default false;
follows the copy-on-write override model like ``is_hidden`` /
``include_in_analytics``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "048"
down_revision: str | None = "047"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "tags",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tags", "is_pinned")
