"""Device push tokens for FCM / UnifiedPush (M11 Sprint 5)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PushProvider(StrEnum):
    FCM = "fcm"
    UNIFIEDPUSH = "unifiedpush"


class PushPlatform(StrEnum):
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"


class DeviceToken(Base):
    """One push registration token per device (upserted by token string)."""

    __tablename__ = "device_tokens"
    __table_args__ = (
        UniqueConstraint("token", name="uq_device_tokens_token"),
        CheckConstraint(
            "provider IN ('fcm', 'unifiedpush')",
            name="ck_device_tokens_provider",
        ),
        CheckConstraint(
            "platform IN ('android', 'ios', 'web')",
            name="ck_device_tokens_platform",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    device_label: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<DeviceToken id={self.id} user_id={self.user_id} "
            f"provider={self.provider!r} platform={self.platform!r}>"
        )
