"""Tag and entry-tag-link models — tag system (M1, Issue #8).

Design notes
------------
- Two tables, not one. ``tags`` holds the tag definition (name, icon,
  category, color, owner). ``entry_tags`` is a thin many-to-many link
  table between :class:`~app.models.entry.Entry` and :class:`Tag`.
- A tag is *either* a curated default (``user_id IS NULL`` and
  ``is_default = TRUE``) *or* a user-owned custom tag (``user_id`` set,
  ``is_default = FALSE``). The DB enforces this with a CHECK constraint
  so neither half of the invariant can drift.
- Default tags are seeded by the migration. They are immutable from the
  application perspective: the API never lets a regular user edit or
  delete a default tag. (DESIGN_DOCUMENT.md §2.2.)
- Categories live as an enum (``sport | social | work | leisure |
  consumption | health | other``) so reports can group without
  clustering on free-text strings. The DESIGN_DOCUMENT lists the first
  five; ``health`` and ``other`` come from real-world usage in early
  drafts (e.g. *medication*, *therapy*) — added now so we don't need a
  destructive migration.
- Uniqueness:
    * Default tags: unique by ``slug``.
    * Custom tags: unique by ``(user_id, slug)`` — a user may not have
      two tags with the same slug, but two different users may.
    * Both invariants live in two partial unique indexes — Postgres
      handles them; SQLAlchemy mirrors them as ``Index(... unique=True,
      postgresql_where=...)``.
- ``slug`` is the lowercase, kebab-cased canonical form (``meditation``,
  ``alkohol``, ``new-friend``). The display name is free-form and
  i18n-safe.
- ``entry_tags`` enforces one row per ``(entry_id, tag_id)`` (no
  duplicate assignments).

Privacy
-------
Tag *names* are not health data on their own (e.g. ``Sport``,
``Meditation``), but a *list of tags assigned to an entry* leaks
behavioural info. The entry-tag link table inherits the same RLS
treatment as ``entries`` (migration 004 — see ``entry_tags_owner_*``
policies). Custom tags created by a user are also user-owned and never
appear in another user's API responses.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TagCategory(StrEnum):
    """Coarse-grained category for grouping in reports.

    The first five (sport / social / work / leisure / consumption) come
    from DESIGN_DOCUMENT.md §2.2; ``health`` and ``other`` cover real
    edge cases (medication, therapy, hobbies that don't fit any other
    bucket) and are added once so the schema stays additive.
    """

    SPORT = "sport"
    SOCIAL = "social"
    WORK = "work"
    LEISURE = "leisure"
    CONSUMPTION = "consumption"
    HEALTH = "health"
    OTHER = "other"


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        # A tag is either curated (user_id NULL, is_default TRUE) or
        # owned by a user (user_id set, is_default FALSE). Neither
        # other combination is valid.
        CheckConstraint(
            "(is_default = TRUE AND user_id IS NULL) "
            "OR (is_default = FALSE AND user_id IS NOT NULL)",
            name="ck_tags_default_owner_consistency",
        ),
        # Slug uniqueness lives in partial indexes (see migration 004) —
        # we cannot express "unique slug among defaults" cleanly with
        # just ``UniqueConstraint`` because user_id NULL would defeat it.
        CheckConstraint(
            "habit_type IN ('none', 'build', 'reduce')", name="ck_tags_habit_type_valid"
        ),
        CheckConstraint(
            "(habit_type = 'none' AND target_frequency IS NULL) "
            "OR (habit_type IN ('build', 'reduce') AND target_frequency BETWEEN 1 AND 7)",
            name="ck_tags_target_frequency_consistent",
        ),
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
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[TagCategory] = mapped_column(
        Enum(TagCategory, name="tag_category", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    # Icon: short string, either an emoji (``"🏃"``) or a Lucide-style
    # icon name (``"dumbbell"``). Both fit in 32 chars.
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Color: 7-char ``#rrggbb`` hex. Validated at the schema layer.
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
        default=False,
    )
    habit_type: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        server_default="none",
        default="none",
    )
    target_frequency: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
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
        # ``name`` is omitted unconditionally; ``slug`` is masked for
        # user-owned tags because it derives from the user-supplied name
        # and can leak it semantically (analog ADR-0005 trade-off for
        # ``Symptom.slug``). Default tag slugs are curated and public.
        if self.is_default:
            return f"<Tag id={self.id} slug={self.slug} default>"
        return f"<Tag id={self.id} slug=<custom> user={self.user_id}>"


class EntryTag(Base):
    """Link row between :class:`~app.models.entry.Entry` and :class:`Tag`.

    Modelled as an explicit row class (not a SQLAlchemy ``Table()``)
    so the ORM can attach RLS-aware queries to it later. ``user_id`` is
    denormalised onto the link row so the RLS policy can match without
    a join — the application is responsible for keeping it in sync with
    the entry's owner (the service layer copies it on insert).
    """

    __tablename__ = "entry_tags"
    __table_args__ = (
        UniqueConstraint("entry_id", "tag_id", name="uq_entry_tags_entry_tag"),
        Index("ix_entry_tags_user_id", "user_id"),
        Index("ix_entry_tags_tag_id", "tag_id"),
    )

    entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<EntryTag entry={self.entry_id} tag={self.tag_id}>"
