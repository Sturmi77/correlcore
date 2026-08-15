"""040 add users.is_admin + backfill existing accounts (#677)

Revision ID: 040
Revises: 039
Create Date: 2026-08-14

Admin-console access flag. The column defaults to ``false`` so every *new*
account is non-admin, but this migration backfills all *pre-existing* accounts
to ``true``: on this instance the current users are the trusted operators, so
the backfill is the admin bootstrap — there is no ADMIN_EMAILS env allowlist.
Grant/revoke thereafter happens in the admin console.

Additive + a one-shot UPDATE: zero-downtime and reversible.
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op

revision: str = "040"
down_revision: str | None = "039"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    # Bootstrap: every account that already exists becomes an admin. New rows
    # keep the server_default of false.
    result = op.get_bind().execute(sa.text("UPDATE users SET is_admin = true"))
    logger.info("040: backfilled is_admin=true on %s existing user(s)", result.rowcount)


def downgrade() -> None:
    op.drop_column("users", "is_admin")
