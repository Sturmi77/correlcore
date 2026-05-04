"""Per-user data-encryption-key (DEK) storage (Issue #26, ADR-0005).

Each authenticated user owns a DEK that encrypts their Art.-9 fields
(``Entry.note_enc``, custom ``Symptom.name_enc``). The DEK is itself
Fernet-encrypted by the master key (``ENCRYPTION_KEY``); only the wrapped
form ever lives in the database.

Privacy
-------
- ``wrapped_dek`` is opaque ciphertext — never logged, never returned via
  the API.
- The row is tied to the user via FK ``ON DELETE CASCADE``: deleting the
  user wipes the wrapped DEK, which makes the user's encrypted payload
  rows cryptographically unrecoverable ("cryptographic erasure" — ADR-0005,
  GDPR Art. 17).

Operations
----------
- ``key_version`` increments on master-key rotation. The Fernet ciphertext
  format already embeds a key generation, so ``MultiFernet.rotate()`` works
  even without our extra column — but the version column lets us track
  rotation progress operationally without decrypting.
- ``rotated_at`` is NULL on initial creation, set to ``now()`` on each
  rotation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserEncryptionKey(Base):
    """One DEK per user, wrapped with the master key."""

    __tablename__ = "user_encryption_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    wrapped_dek: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug only
        # Never expose the wrapped DEK, even by length.
        return f"<UserEncryptionKey user_id={self.user_id} version={self.key_version}>"
