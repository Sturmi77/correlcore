"""Entry note markers (legacy) and signals (Notes in Analysis foundation).

``entry_note_markers`` is dropped by migration 049 (#903 C). The
``EntryNoteMarker`` ORM model remains only so the one-off marker→tag
backfill can run *during* that upgrade before the DROP. Note signals stay.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NoteMarkerSource(StrEnum):
    USER = "user"
    SUGGESTION = "suggestion"


class EntryNoteMarker(Base):
    """Legacy marker rows — readable until migration 049 drops the table."""

    __tablename__ = "entry_note_markers"
    __table_args__ = (
        UniqueConstraint("entry_id", "marker", name="uq_entry_note_markers_entry_marker"),
        CheckConstraint(
            "source IN ('user', 'suggestion')",
            name="ck_entry_note_markers_source_allowed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    marker: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[NoteMarkerSource] = mapped_column(
        Text,
        nullable=False,
        default=NoteMarkerSource.USER,
        server_default=NoteMarkerSource.USER.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )


class EntryNoteSignal(Base):
    __tablename__ = "entry_note_signals"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_entry_note_signals_confidence_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    source_span: Mapped[str | None] = mapped_column(Text, nullable=True)
    extractor_v: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
