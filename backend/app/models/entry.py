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
- ``note_enc`` holds the user's freeform note as Fernet ciphertext under
  the request-bound per-user DEK (ADR-0005 / Issue #26). The
  ``EncryptedString`` TypeDecorator keeps service and schema code working
  with ``str | None`` while the database stores opaque ``BYTEA`` tokens.
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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.crypto import EncryptedString
from app.db.base import Base


class EntrySlot(StrEnum):
    """Time-of-day slot for an entry. M1 uses DAY only; reserved for M3+."""

    DAY = "day"
    MORNING = "morning"
    NOON = "noon"
    EVENING = "evening"


class EntrySource(StrEnum):
    """How an entry was captured."""

    DIRECT = "direct"
    RETROSPECTIVE = "retrospective"
    IMPORT = "import"
    WEARABLE = "wearable"


class NoteVisibility(StrEnum):
    """Per-entry note display/analysis opt-out (notes-in-analysis spec)."""

    FULL = "full"
    ANALYSIS_ONLY = "analysis_only"
    HIDDEN = "hidden"


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
        CheckConstraint(
            "cycle_day IS NULL OR cycle_day BETWEEN 1 AND 35",
            name="ck_entries_cycle_day_range",
        ),
        CheckConstraint(
            "note_visibility IN ('full', 'analysis_only', 'hidden')",
            name="ck_entries_note_visibility_allowed",
        ),
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
    cycle_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[EntrySource] = mapped_column(
        Enum(EntrySource, name="entry_source", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=EntrySource.DIRECT,
        server_default=EntrySource.DIRECT.value,
    )
    work_context: Mapped[WorkContext] = mapped_column(
        Enum(WorkContext, name="work_context", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    # note_enc holds the user's freeform note. It is stored as a Fernet token
    # (BYTEA) under the user's per-user DEK; the EncryptedString TypeDecorator
    # makes the conversion transparent (string in, string out) as long as the
    # request DEK is bound via app.core.crypto.set_current_user_dek().
    # Issue #26 / ADR-0005.
    note_enc: Mapped[str | None] = mapped_column(
        EncryptedString,
        nullable=True,
    )
    note_summary_short: Mapped[str | None] = mapped_column(nullable=True)
    note_visibility: Mapped[NoteVisibility] = mapped_column(
        nullable=False,
        default=NoteVisibility.FULL,
        server_default=NoteVisibility.FULL.value,
    )
    note_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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
