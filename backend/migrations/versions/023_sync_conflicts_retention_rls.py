"""023 sync_conflicts retention DELETE policy (M4.1.1 #258)

Revision ID: 023
Revises: 022
Create Date: 2026-07-15

Allows the analytics/cleanup worker to delete stale conflict rows without
binding ``app.current_user_id`` (owner-only RLS previously matched 0 rows).
"""

from __future__ import annotations

from alembic import op

revision: str = "023"
down_revision: str | None = "022"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE POLICY sync_conflicts_retention_delete ON sync_conflicts
        FOR DELETE
        USING (NULLIF(current_setting('app.sync_retention', true), '') = 'true')
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS sync_conflicts_retention_delete ON sync_conflicts")
