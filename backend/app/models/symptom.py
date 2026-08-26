"""Symptom model — health-symptom catalogue & per-entry log (Issue #57, ADR-0008).

Design notes
------------
- ``Symptom`` is the master catalogue (analog to :class:`~app.models.tag.Tag`).
  Curated/default symptoms have ``user_id IS NULL`` and ``is_default=True``;
  custom user-created symptoms have ``user_id`` set and ``is_default=False``.
  A CHECK constraint enforces this exclusivity. Slug uniqueness is provided
  by **partial indexes** in migration 006 (one for defaults, one per user).
- ``EntrySymptom`` is the per-entry log row that references a Symptom by
  FK ``symptom_id``. There is one row per ``(entry_id, symptom_id)`` —
  the same symptom can't be logged twice on the same entry.
- ``intensity`` is 0..3 (DESIGN_DOCUMENT.md §2.3, Issue #9):
    * 0 = abwesend / nicht relevant
    * 1 = leicht
    * 2 = mittel
    * 3 = stark
  A CHECK constraint enforces the range; the UI maps it to a visual
  scale (4 dots), not a raw number input.
- ``user_id`` is denormalised onto every ``entry_symptoms`` row so RLS
  policies can match without joining ``entries``. The service layer copies
  it from the owning entry on insert.

Standard symptom keys
---------------------
``STANDARD_SYMPTOM_KEYS`` lists the slugs migration 006 inserts as
default rows. Adding a new default needs:
  1. A new entry here.
  2. A migration that ``INSERT``s the row (use ``uuid5(NAMESPACE_DNS, slug)``
     for a deterministic, idempotent UUID).
  3. An i18n entry in the frontend (``symptom.default.<slug>``).

Privacy
-------
**Symptoms are health data under DSGVO Art. 9.** The combination of a
symptom name and ``intensity`` is sensitive on its own and must never
appear in application logs (see ``test_log_scrubbing.py``). User-created
custom names are likewise Art.-9-relevant and are stored in
``Symptom.name_enc`` as Fernet ciphertext under the owner's per-user DEK
(ADR-0005 / Issue #26). Curated defaults keep ``name`` plaintext because
those labels are non-personal catalogue data and must be readable without
an authenticated DEK context.

The standard symptom set is intentionally short and physiological; we
deliberately do not seed mental-health keys in M1 to avoid creating a
quasi-diagnostic surface (DESIGN_DOCUMENT.md §6 medical disclaimer —
CorrelCore is not a diagnostic tool).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.crypto import decrypt_with_dek, encrypt_with_dek, get_current_user_dek
from app.db.base import Base

# ---------------------------------------------------------------------------
# Standard symptom set (M1 default seed)
# ---------------------------------------------------------------------------
#
# Slugs of the curated default symptoms. Migrations 006 and 043 insert one
# ``Symptom`` row per slug with ``is_default=True`` and a deterministic
# UUID5 (``NAMESPACE_DNS`` + slug) so the migration is idempotent against
# re-runs.

STANDARD_SYMPTOM_KEYS: tuple[str, ...] = (
    "headache",
    "digestion",
    "back_pain",
    "fatigue",
    "cold",
    "migraine",
    "nausea",
    "dizziness",
)

# Bounds for the intensity scale (0 = absent, 3 = strong). Mirrored in
# the schema layer and the DB CHECK constraint.
INTENSITY_MIN = 0
INTENSITY_MAX = 3


def default_symptom_uuid(slug: str) -> uuid.UUID:
    """Deterministic UUID for a default symptom slug.

    Used by migration 006's seed step so re-running the migration on a
    fresh database yields the same UUIDs as the first run, and so seed
    rows are de-duplicable across environments without extra lookup
    columns.
    """
    # Keep the original namespace stable so renamed builds preserve default IDs.
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"moodsync.symptom.{slug}")


class Symptom(Base):
    """Symptom master row — either a curated default or a user-owned custom."""

    __tablename__ = "symptoms"
    __table_args__ = (
        # A symptom is either curated (user_id NULL, is_default TRUE) or
        # owned by a user (user_id set, is_default FALSE). No other
        # combination is valid.
        CheckConstraint(
            "(is_default = TRUE AND user_id IS NULL) "
            "OR (is_default = FALSE AND user_id IS NOT NULL)",
            name="ck_symptoms_default_owner_consistency",
        ),
        # Issue #26 / ADR-0005: encrypted name storage for custom symptoms.
        # Defaults keep ``name`` plaintext (no DEK available without an owner);
        # custom symptoms carry their Art.-9-relevant name in ``name_enc`` as
        # a Fernet token under the owner's DEK and leave ``name`` NULL.
        # The CHECK below enforces the exclusivity at DB level.
        CheckConstraint(
            "(is_default = TRUE AND name IS NOT NULL AND name_enc IS NULL) "
            "OR (is_default = FALSE AND name IS NULL AND name_enc IS NOT NULL)",
            name="ck_symptoms_name_storage_consistency",
        ),
        # Slug uniqueness lives in partial indexes (see migration 006) —
        # we cannot express "unique slug among defaults" cleanly with a
        # single ``UniqueConstraint`` because user_id NULL would defeat it.
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    # ``name`` is plaintext for default symptoms only (Art.-9 risk acceptable
    # because defaults are non-personal medical labels). Custom symptoms keep
    # ``name`` NULL and store the Fernet ciphertext in ``name_enc`` instead.
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # Icon: short string, either an emoji ("🤕") or a Lucide-style
    # icon name ("brain"). Both fit in 32 chars.
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        default=False,
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

    @property
    def display_name(self) -> str:
        """Plaintext name regardless of storage column.

        - For default symptoms returns ``self.name`` (already plaintext).
        - For custom symptoms decrypts ``self.name_enc`` using the request's
          DEK from :func:`app.core.crypto.get_current_user_dek`. Raises
          :class:`~app.core.crypto.DekUnavailableError` if no DEK is bound
          (e.g. unauthenticated context).
        """
        if self.is_default:
            # Defensive: ``name`` is enforced NOT NULL for defaults via CHECK,
            # but mypy needs a guard.
            return self.name or ""
        if self.name_enc is None:
            return ""
        return decrypt_with_dek(self.name_enc, get_current_user_dek())

    def set_custom_name(self, plaintext: str) -> None:
        """Encrypt ``plaintext`` with the request DEK and store in ``name_enc``.

        Use this on the service layer when creating/updating a custom
        symptom. Defaults must use the ``name`` column directly (only the
        seed migration writes those rows).
        """
        if self.is_default:
            raise ValueError("set_custom_name() is for custom symptoms only")
        self.name = None
        self.name_enc = encrypt_with_dek(plaintext, get_current_user_dek())

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        # Deliberately omits ``name`` — log-scrubbing rule bans Art.-9
        # symptom payloads (incl. custom names) from logs.
        # For custom symptoms the slug derives from the user-supplied name
        # (ADR-0005 plaintext trade-off) and can semantically leak the
        # symptom name, so we mask it here. Default slugs are public.
        if self.is_default:
            return f"<Symptom id={self.id} slug={self.slug} default>"
        return f"<Symptom id={self.id} slug=<custom> user={self.user_id}>"


class EntrySymptom(Base):
    """One symptom log row attached to an entry."""

    __tablename__ = "entry_symptoms"
    __table_args__ = (
        UniqueConstraint(
            "entry_id",
            "symptom_id",
            name="uq_entry_symptoms_entry_symptom",
        ),
        CheckConstraint(
            f"intensity BETWEEN {INTENSITY_MIN} AND {INTENSITY_MAX}",
            name="ck_entry_symptoms_intensity_range",
        ),
        Index("ix_entry_symptoms_symptom_id", "symptom_id"),
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
    symptom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("symptoms.id", ondelete="CASCADE"),
        nullable=False,
    )
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
        # Deliberately omits intensity & symptom_id payload — log-scrubbing
        # rule (test_log_scrubbing.py) bans symptom payloads from logs.
        return f"<EntrySymptom id={self.id} entry={self.entry_id}>"
