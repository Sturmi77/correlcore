"""Sync conflict log model (M4.1, Issue #24, ADR-0003 / ADR-0036).

Each row records a field-level Last-Write-Wins merge where the client and
server timestamps diverged. The winning value remains in the primary entity
table; this table is append-only audit metadata for user transparency.

Privacy: ``client_value`` / ``server_value`` for ``note`` conflicts must
never contain plaintext — only redacted markers (ADR-0036 §2.1).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SyncConflictEntityType(StrEnum):
    ENTRY = "entry"
    TAG = "tag"
    SYMPTOM = "symptom"


class SyncConflict(Base):
    __tablename__ = "sync_conflicts"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('entry', 'tag', 'symptom')",
            name="ck_sync_conflicts_entity_type",
        ),
        Index("ix_sync_conflicts_user_created_at", "user_id", "created_at"),
        Index("ix_sync_conflicts_entity_id", "entity_id"),
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
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    field_name: Mapped[str] = mapped_column(Text, nullable=False)
    client_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    server_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    client_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    server_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<SyncConflict id={self.id} user_id={self.user_id} "
            f"entity={self.entity_type}:{self.entity_id} field={self.field_name}>"
        )
