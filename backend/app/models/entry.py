"""Entry model — daily mood/energy/stress log (M1, Issue #7).

Design notes
------------
- ``user_id`` FK on every entity (ADR / DESIGN_DOCUMENT.md §3.5);
  Row-Level-Security policies enforce isolation at DB level (added
  in migration 003).
- One entry per ``(user_id, entry_date, slot)`` — slot defaults to
  ``day`` (DESIGN_DOCUMENT.md §2.1). Multi-slot tracking arrives in M3+;
  the column is reserved here so we don't need a destructive migration.
- ``mood_score`` / ``energy`` / ``stress`` are 1..5 integers with a
  CHECK constraint. The slider in the UI maps directly onto this range.
- ``work_context`` is an enum: ``homeoffice | office | vacation | sick |
  weekend | travel`` (DESIGN_DOCUMENT.md §2.7).
- ``note_enc`` holds the user's freeform note. The column is named
  ``_enc`` because Issue #26 will swap the plaintext bytes for Fernet-
  encrypted ciphertext (ADR-0005). For M1 we accept plaintext UTF-8 and
  document the upgrade path in CHANGELOG; the schema is already correct.
- All timestamps in UTC (``timezone=True``) with a Postgres trigger
  keeping ``updated_at`` fresh (created in migration 003 and reusing
  the ``update_updated_at_column`` function from migration 001).

Privacy
-------
The Entry is the most sensitive entity in the system: mood, stress and
notes must never leak into logs. The log-scrubber test
(:mod:`backend.tests.test_log_scrubbing`) is extended in PR-side tests
to cover ``mood_score``, ``energy``, ``stress`` and ``note_enc``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from datetime import date as date_type
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EntrySlot(StrEnum):
    """Time-of-day slot for an entry. M1 uses DAY only; reserved for M3+."""

    DAY = "day"
    MORNING = "morning"
    NOON = "noon"
    EVENING = "evening"


class WorkContext(StrEnum):
    """User's working/life context for the day (DESIGN_DOCUMENT.md §2.7)."""

    HOMEOFFICE = "homeoffice"
    OFFICE = "office"
    VACATION = "vacation"
    SICK = "sick"
    WEEKEND = "weekend"
    TRAVEL = "travel"


class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = (
        UniqueConstraint("user_id", "entry_date", "slot", name="uq_entries_user_date_slot"),
        CheckConstraint("mood_score BETWEEN 1 AND 5", name="ck_entries_mood_score_range"),
        CheckConstraint("energy BETWEEN 1 AND 5", name="ck_entries_energy_range"),
        CheckConstraint("stress BETWEEN 1 AND 5", name="ck_entries_stress_range"),
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
        index=True,
    )
    entry_date: Mapped[date_type] = mapped_column(
        Date,
        nullable=False,
    )
    slot: Mapped[EntrySlot] = mapped_column(
        Enum(EntrySlot, name="entry_slot", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=EntrySlot.DAY,
        server_default=EntrySlot.DAY.value,
    )
    mood_score: Mapped[int] = mapped_column(Integer, nullable=False)
    energy: Mapped[int] = mapped_column(Integer, nullable=False)
    stress: Mapped[int] = mapped_column(Integer, nullable=False)
    work_context: Mapped[WorkContext] = mapped_column(
        Enum(WorkContext, name="work_context", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    note_enc: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        default=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<Entry id={self.id} user_id={self.user_id} "
            f"date={self.entry_date} slot={self.slot.value}>"
        )
