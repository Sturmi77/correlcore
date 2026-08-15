"""Append-only audit log for admin-console actions (#677).

Deliberately **no FK** to ``users`` on either the actor or the target:
- the target column must survive the very deletion it records, and
- an audit trail must outlive an actor whose account is later removed.

Both ids are therefore plain UUID columns; the (readable) emails are stored
alongside so the log stays intelligible after the rows are gone. This is an
operator-facing admin audit — recording who deleted/disabled/reset whom is the
legitimate purpose, distinct from application logs (which keep PII out).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Known admin actions — extend as the console grows.
ADMIN_ACTION_DELETE_USER = "delete_user"
ADMIN_ACTION_DISABLE_USER = "disable_user"
ADMIN_ACTION_ENABLE_USER = "enable_user"
ADMIN_ACTION_TRIGGER_PASSWORD_RESET = "trigger_password_reset"


class AdminAuditLog(Base):
    """One row per sensitive admin-console action."""

    __tablename__ = "admin_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    actor_email: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    target_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
