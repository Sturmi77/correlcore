"""012 enforce RLS and grant app role privileges

Revision ID: 012
Revises: 011
Create Date: 2026-05-21
"""

from __future__ import annotations

from alembic import op

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


_RLS_TABLES = (
    "entries",
    "tags",
    "entry_tags",
    "entry_symptoms",
    "symptoms",
    "user_encryption_keys",
    "insights",
    "user_preferences",
    "user_profiles",
)


def upgrade() -> None:
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'correlcore_app') THEN
                GRANT USAGE ON SCHEMA public TO correlcore_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public
                    TO correlcore_app;
                GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public
                    TO correlcore_app;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO correlcore_app;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO correlcore_app;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    for table in reversed(_RLS_TABLES):
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
