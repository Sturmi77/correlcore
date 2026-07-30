"""033 preserve explicit updated_at on sync LWW writes

Revision ID: 033
Revises: 032
Create Date: 2026-07-27

The shared ``update_updated_at_column()`` trigger (migration 001) previously
unconditionally overwrote ``NEW.updated_at = now()`` on every UPDATE. Offline
sync LWW deliberately sets ``entry/tag/symptom.updated_at = client_ts`` before
flush; the trigger then replaced that client timestamp with server receive
time, so a later device with a real client timestamp between the original
client_ts and receive time lost the write.

Preserve caller-supplied ``updated_at`` values; only auto-bump when the UPDATE
did not change the column (REST/ORM paths that leave it untouched).
"""

from __future__ import annotations

from alembic import op

revision: str = "033"
down_revision: str | None = "032"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


_PRESERVE_EXPLICIT = """
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.updated_at IS NOT DISTINCT FROM OLD.updated_at THEN
        NEW.updated_at = now();
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';
"""

_UNCONDITIONAL = """
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';
"""


def upgrade() -> None:
    op.execute(_PRESERVE_EXPLICIT)


def downgrade() -> None:
    op.execute(_UNCONDITIONAL)
