"""031 backfill legacy digest_enabled rows to false (opt-in policy)

Revision ID: 031
Revises: 030
Create Date: 2026-07-23

Migration 026 added ``digest_enabled`` as NOT NULL DEFAULT true, and the ORM
model carried ``default=True`` as well until #398. Every preference row that
existed or was created before that upgrade therefore holds ``true`` without
the user ever having opted in. Migration 028 only changed the column default;
it deliberately left those rows alone.

The digest worker gates on ``digest_enabled IS TRUE`` and documents that as
"require an explicit opt-in", which was not true for those rows — they would
have received weekly digests they never asked for.

This resets every ``true`` row once, unconditionally.

Why not bound it by ``created_at``: nothing records when 028 was applied to a
given database, so any date cutoff is a guess that silently mis-classifies
late upgraders in both directions. The two failure modes are not symmetric —
resetting a genuine opt-in is visible and one click to undo in Settings, while
leaving an artifact sends mail nobody consented to. On top of that, the digest
worker only runs behind an opt-in compose profile (``COMPOSE_PROFILES=digest``),
so no row's ``true`` has ever produced a delivery and nothing real is lost.

Operators must mention in release notes that digest recipients re-enable the
toggle under Settings → Analysis.
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from alembic import op

revision: str = "031"
down_revision: str | None = "030"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    conn = op.get_bind()

    # ``user_preferences`` runs under FORCE ROW LEVEL SECURITY (migrations 010 +
    # 012) with policies keyed on ``app.current_user_id``, which no migration
    # sets. A role that neither bypasses RLS nor is superuser would therefore
    # update zero rows and report success — the one failure mode of this
    # migration that nobody would notice. Fail loudly instead.
    privileged = conn.execute(
        sa.text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user")
    ).scalar()
    if not privileged:
        raise RuntimeError(
            "Migration 031 must run as a superuser or a BYPASSRLS role: "
            "user_preferences enforces FORCE ROW LEVEL SECURITY, so a restricted "
            "role would silently reset nothing. Run migrations as the database "
            "owner (the same role used for every earlier migration)."
        )

    result = conn.execute(
        sa.text("UPDATE user_preferences SET digest_enabled = false WHERE digest_enabled = true")
    )
    logger.info("031: reset digest_enabled on %s legacy row(s)", result.rowcount)


def downgrade() -> None:
    """No-op on purpose.

    Which rows were reset is not recorded, so restoring them would mean
    re-enabling the digest for users who never opted in — reintroducing the
    exact defect this migration fixes. Downgrading leaves everyone opted out;
    re-enable via Settings.
    """
