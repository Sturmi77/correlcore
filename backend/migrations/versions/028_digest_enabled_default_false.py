"""028 digest_enabled default false (opt-in weekly digest)

Revision ID: 028
Revises: 027
Create Date: 2026-07-16

Weekly digest delivery is opt-in until the scheduled worker is enabled in
compose. New preference rows default to ``false``. Existing rows are left
unchanged so operators who already opted in keep their choice.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "028"
down_revision: str | None = "027"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.alter_column(
        "user_preferences",
        "digest_enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "user_preferences",
        "digest_enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )
