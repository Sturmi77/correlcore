"""EmailVerificationToken model — single-use email verification tokens.

Design (ADR-0004, Issue #39):
- ``token_hash`` is SHA-256(plaintext) — the plaintext is delivered only
  via email and is never persisted anywhere on the server.
- ``used_at`` enforces single-use semantics; combined with ``expires_at``
  this gives revocation + replay protection.
- ``ON DELETE CASCADE`` on user_id ensures DSGVO Art. 17 erasure cleans
  the token table without orphans.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

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
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return (
            f"<EmailVerificationToken id={self.id} user_id={self.user_id} "
            f"used={'yes' if self.used_at else 'no'}>"
        )
