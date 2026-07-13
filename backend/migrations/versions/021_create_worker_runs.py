"""021 create worker_runs

Revision ID: 021
Revises: 020
Create Date: 2026-07-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "021"
down_revision: str | None = "020"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    worker_job_kind = postgresql.ENUM(
        "daily_bundle",
        "insights",
        "cleanup",
        "user_insights",
        name="worker_job_kind",
        create_type=False,
    )
    worker_trigger_source = postgresql.ENUM(
        "scheduled",
        "cli_once",
        "admin_trigger",
        "user_regenerate",
        "post_batch",
        "dev_trigger",
        name="worker_trigger_source",
        create_type=False,
    )
    worker_run_status = postgresql.ENUM(
        "running",
        "succeeded",
        "failed",
        name="worker_run_status",
        create_type=False,
    )
    worker_job_kind.create(op.get_bind(), checkfirst=True)
    worker_trigger_source.create(op.get_bind(), checkfirst=True)
    worker_run_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "worker_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_name", sa.String(length=64), nullable=False),
        sa.Column("job_kind", worker_job_kind, nullable=False),
        sa.Column("trigger_source", worker_trigger_source, nullable=False),
        sa.Column(
            "status",
            worker_run_status,
            nullable=False,
            server_default="running",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["scope_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_worker_runs_started_at", "worker_runs", ["started_at"])
    op.create_index(
        "ix_worker_runs_worker_kind_started",
        "worker_runs",
        ["worker_name", "job_kind", "started_at"],
    )
    op.create_index(
        "ix_worker_runs_scope_user_started",
        "worker_runs",
        ["scope_user_id", "started_at"],
    )

    # Operational telemetry: visible across users on /dev; not Art. 9 content.
    op.execute("ALTER TABLE worker_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE worker_runs FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY worker_runs_app_select ON worker_runs
        FOR SELECT USING (true)
        """
    )
    op.execute(
        """
        CREATE POLICY worker_runs_app_insert ON worker_runs
        FOR INSERT WITH CHECK (true)
        """
    )
    op.execute(
        """
        CREATE POLICY worker_runs_app_update ON worker_runs
        FOR UPDATE USING (true) WITH CHECK (true)
        """
    )
    op.execute(
        """
        CREATE POLICY worker_runs_app_delete ON worker_runs
        FOR DELETE USING (true)
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'correlcore_app') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON worker_runs TO correlcore_app;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    for action in ("delete", "update", "insert", "select"):
        op.execute(f"DROP POLICY IF EXISTS worker_runs_app_{action} ON worker_runs")
    op.execute("ALTER TABLE worker_runs NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE worker_runs DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_worker_runs_scope_user_started", table_name="worker_runs")
    op.drop_index("ix_worker_runs_worker_kind_started", table_name="worker_runs")
    op.drop_index("ix_worker_runs_started_at", table_name="worker_runs")
    op.drop_table("worker_runs")
    op.execute("DROP TYPE IF EXISTS worker_run_status")
    op.execute("DROP TYPE IF EXISTS worker_trigger_source")
    op.execute("DROP TYPE IF EXISTS worker_job_kind")
