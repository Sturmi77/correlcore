"""Persisted weekly insight digest snapshots for push delivery."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from datetime import date as date_type

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InsightDigest(Base):
    """One stored weekly digest per user run."""

    __tablename__ = "insight_digests"
    __table_args__ = (
        Index("ix_insight_digests_user_generated_at", "user_id", "generated_at"),
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
    week_start: Mapped[date_type] = mapped_column(Date, nullable=False)
    week_end: Mapped[date_type] = mapped_column(Date, nullable=False)
    insight_ids: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    insight_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    push_title: Mapped[str] = mapped_column(Text, nullable=False)
    push_body: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
