"""Subject-stable insight dismissal rows (#601 Phase 1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InsightDismissal(Base):
    """One hide intent per user + semantic subject key.

    Survives insight row regeneration (new UUIDs) because matching uses
    ``subject_key``, not ``insight_id``. ``insight_id`` is a hydration hint.
    """

    __tablename__ = "insight_dismissals"
    __table_args__ = (
        UniqueConstraint("user_id", "subject_key", name="uq_insight_dismissals_user_subject"),
        Index("ix_insight_dismissals_user_id", "user_id"),
        Index("ix_insight_dismissals_user_dismissed_at", "user_id", "dismissed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    insight_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("insights.id", ondelete="SET NULL"),
        nullable=True,
    )
    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<InsightDismissal id={self.id} user_id={self.user_id}>"
