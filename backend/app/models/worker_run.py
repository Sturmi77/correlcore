"""Persisted worker/job run telemetry for developer diagnostics."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkerJobKind(StrEnum):
    """Coarse job families recorded by the analytics worker."""

    DAILY_BUNDLE = "daily_bundle"
    INSIGHTS = "insights"
    CLEANUP = "cleanup"
    DIGEST = "digest"
    USER_INSIGHTS = "user_insights"


class WorkerTriggerSource(StrEnum):
    """How a worker run was started."""

    SCHEDULED = "scheduled"
    CLI_ONCE = "cli_once"
    ADMIN_TRIGGER = "admin_trigger"
    USER_REGENERATE = "user_regenerate"
    POST_BATCH = "post_batch"
    DEV_TRIGGER = "dev_trigger"


class WorkerRunStatus(StrEnum):
    """Lifecycle status of a recorded worker run."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class WorkerRun(Base):
    """One started/finished worker execution, used by the /dev worker view."""

    __tablename__ = "worker_runs"
    __table_args__ = (
        Index("ix_worker_runs_started_at", "started_at"),
        Index("ix_worker_runs_worker_kind_started", "worker_name", "job_kind", "started_at"),
        Index("ix_worker_runs_scope_user_started", "scope_user_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    worker_name: Mapped[str] = mapped_column(String(64), nullable=False, default="analytics")
    job_kind: Mapped[WorkerJobKind] = mapped_column(
        Enum(
            WorkerJobKind,
            name="worker_job_kind",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    trigger_source: Mapped[WorkerTriggerSource] = mapped_column(
        Enum(
            WorkerTriggerSource,
            name="worker_trigger_source",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    status: Mapped[WorkerRunStatus] = mapped_column(
        Enum(
            WorkerRunStatus,
            name="worker_run_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=WorkerRunStatus.RUNNING,
        server_default=WorkerRunStatus.RUNNING.value,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    result: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<WorkerRun id={self.id} worker={self.worker_name} "
            f"kind={self.job_kind.value} status={self.status.value}>"
        )
