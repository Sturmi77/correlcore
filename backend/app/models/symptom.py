"""Symptom model — health-symptom checklist (M1, Issue #9).

Design notes
------------
- Symptoms are modelled as a per-entry log row (``entry_symptoms``),
  not as a separate master table. The standard symptom keys
  (``headache | digestion | back_pain | fatigue | cold``) form a
  closed set seeded in migration 005 — there is no user-managed
  custom-symptom catalogue in M1.
- ``symptom_key`` is a string column constrained at the DB level to the
  seeded set so a typo can't slip through. (We avoid a Postgres ENUM
  for now: extending an enum requires a migration that locks the
  table; a CHECK ... IN (...) is just as strict and trivially editable.
  The standard set is small and stable.)
- ``intensity`` is 0..3 (DESIGN_DOCUMENT.md §2.3, Issue #9):
    * 0 = abwesend / nicht relevant
    * 1 = leicht
    * 2 = mittel
    * 3 = stark
  A CHECK constraint enforces the range; the UI maps it to a visual
  scale (4 dots), not a raw number input.
- Uniqueness: one row per ``(entry_id, symptom_key)`` — the same
  symptom can't be logged twice on the same entry. PUT semantics on
  the API replace the entire set so duplicate-key collisions never
  happen at the wire layer.
- ``user_id`` is denormalised onto every row so RLS policies can match
  without joining ``entries``. The service layer copies it from the
  owning entry on insert.

Privacy
-------
**Symptoms are health data under DSGVO Art. 9.** The combination of
``symptom_key`` and ``intensity`` is sensitive on its own and must
never appear in application logs (see ``test_log_scrubbing.py``).
Issue #26 will add Fernet at-rest encryption for the columns; for M1
we store plaintext and document the upgrade path in CHANGELOG. The
table-level RLS policies (migration 005) prevent cross-user reads at
the DB level even before app-level encryption lands.

The standard symptom set is intentionally short and physiological;
we deliberately do not seed mental-health keys in M1 to avoid
creating a quasi-diagnostic surface (DESIGN_DOCUMENT.md §6 medical
disclaimer — MoodSync is not a diagnostic tool).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ---------------------------------------------------------------------------
# Standard symptom set (M1)
# ---------------------------------------------------------------------------
#
# Mirrored exactly in migration 005's CHECK constraint and in the seed
# emitted by ``seed_standard_symptom_keys`` (the migration only seeds
# the *constraint*, not data — there are no rows until users log
# symptoms). Adding a new key needs:
#   1. A new line here.
#   2. A migration that ALTERs the CHECK list.
#   3. An i18n entry in the frontend.

STANDARD_SYMPTOM_KEYS: frozenset[str] = frozenset(
    {
        "headache",
        "digestion",
        "back_pain",
        "fatigue",
        "cold",
    }
)

# Bounds for the intensity scale (0 = absent, 3 = strong). Mirrored in
# the schema layer and the DB CHECK constraint.
INTENSITY_MIN = 0
INTENSITY_MAX = 3


class EntrySymptom(Base):
    """One symptom log row attached to an entry."""

    __tablename__ = "entry_symptoms"
    __table_args__ = (
        UniqueConstraint(
            "entry_id",
            "symptom_key",
            name="uq_entry_symptoms_entry_symptom",
        ),
        CheckConstraint(
            f"intensity BETWEEN {INTENSITY_MIN} AND {INTENSITY_MAX}",
            name="ck_entry_symptoms_intensity_range",
        ),
        # The allowed-keys CHECK lives in the migration so it can be
        # ALTERed without touching the model. The model only knows the
        # canonical Python-side constant ``STANDARD_SYMPTOM_KEYS``.
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
    symptom_key: Mapped[str] = mapped_column(String(64), nullable=False)
    intensity: Mapped[int] = mapped_column(Integer, nullable=False)
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
        # Deliberately omits intensity & key — log-scrubbing rule
        # (test_log_scrubbing.py) bans symptom payloads from logs.
        return f"<EntrySymptom id={self.id} entry={self.entry_id}>"
