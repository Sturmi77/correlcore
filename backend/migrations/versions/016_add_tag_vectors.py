"""016 add tag vectors for M7 clustering

Revision ID: 016
Revises: 015
Create Date: 2026-05-31
"""

from __future__ import annotations

from alembic import op

revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE tag_vectors (
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            embedding vector NOT NULL,
            tag_order JSONB NOT NULL DEFAULT '[]'::jsonb,
            window_start DATE NOT NULL,
            window_end DATE NOT NULL,
            entry_count INTEGER NOT NULL,
            active_tag_count INTEGER NOT NULL,
            computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, tag_id),
            CONSTRAINT ck_tag_vectors_entry_count_nonnegative CHECK (entry_count >= 0),
            CONSTRAINT ck_tag_vectors_active_tag_count_nonnegative CHECK (active_tag_count >= 0)
        )
        """
    )
    op.execute("CREATE INDEX ix_tag_vectors_user_computed_at ON tag_vectors (user_id, computed_at)")
    op.execute("ALTER TABLE tag_vectors ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tag_vectors FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tag_vectors_owner_select ON tag_vectors
        FOR SELECT
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY tag_vectors_owner_insert ON tag_vectors
        FOR INSERT
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY tag_vectors_owner_update ON tag_vectors
        FOR UPDATE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY tag_vectors_owner_delete ON tag_vectors
        FOR DELETE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'correlcore_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON tag_vectors TO correlcore_app;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tag_vectors")
