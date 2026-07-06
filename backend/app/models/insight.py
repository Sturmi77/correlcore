"""Insight persistence model for the M3 analytics foundation.

The worker and API routes are intentionally not part of this sprint. This
module only defines the stable storage contract that later analytics code will
write to after applying minimum-sample and confidence gates.
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
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.crypto import EncryptedString
from app.db.base import Base


class InsightType(StrEnum):
    """Supported insight families.

    The values are storage/API values; display wording is a frontend/i18n
    concern and must stay neutral under the No-Gamification principle.
    """

    POINTBISERIAL = "pointbiserial"
    SPEARMAN = "spearman"
    WEEKDAY_PATTERN = "weekday_pattern"
    WORK_CONTEXT_PATTERN = "work_context_pattern"
    WEEKDAY_CONTEXT_PATTERN = "weekday_context_pattern"
    SYMPTOM_CLUSTER = "symptom_cluster"
    SYMPTOM_MOOD_ASSOCIATION = "symptom_mood_association"
    SYMPTOM_TAG_COOCCURRENCE = "symptom_tag_cooccurrence"


class InsightTier(StrEnum):
    """Confidence tier assigned by analytics gates."""

    NONE = "none"
    EARLY = "early"
    PRELIMINARY = "preliminary"
    DEVELOPING = "developing"
    ROBUST = "robust"


class Insight(Base):
    """Persisted analytics insight owned by one user."""

    __tablename__ = "insights"
    __table_args__ = (
        Index("ix_insights_user_id", "user_id"),
        Index("ix_insights_user_generated_at", "user_id", "generated_at"),
        Index("ix_insights_user_type_metric", "user_id", "insight_type", "metric"),
        CheckConstraint("sample_n >= 0", name="ck_insights_sample_n_nonnegative"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_insights_confidence_range",
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
    )
    insight_type: Mapped[InsightType] = mapped_column(
        Enum(InsightType, name="insight_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    tier: Mapped[InsightTier] = mapped_column(
        Enum(InsightTier, name="insight_tier", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=InsightTier.NONE,
        server_default=InsightTier.NONE.value,
    )
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    subject_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    effect_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_n: Mapped[int] = mapped_column(Integer, nullable=False)
    statement_enc: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    flags: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    payload: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    generated_for_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
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
            f"<Insight id={self.id} user_id={self.user_id} "
            f"type={self.insight_type.value} tier={self.tier.value}>"
        )
