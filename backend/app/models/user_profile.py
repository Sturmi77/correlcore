"""Optional onboarding profile for cold-start insight previews."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SleepHoursTypical(StrEnum):
    H5 = "5h"
    H6 = "6h"
    H7 = "7h"
    H8 = "8h"
    H9_PLUS = "9h_plus"


class WorkContextTypical(StrEnum):
    OFFICE = "office"
    HYBRID = "hybrid"
    REMOTE = "remote"
    OTHER = "other"


class SportFrequency(StrEnum):
    RARELY = "rarely"
    WEEKLY_1_2 = "1_2_week"
    WEEKLY_3_4 = "3_4_week"
    DAILY = "daily"


class InsightCuriosity(StrEnum):
    WORK_LIFE = "work_life"
    ENERGY_SLEEP = "energy_sleep"
    HABITS_SPORT = "habits_sport"
    WELLBEING = "wellbeing"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    sleep_hours_typical: Mapped[SleepHoursTypical | None] = mapped_column(
        Enum(
            SleepHoursTypical,
            name="sleep_hours_typical",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=True,
    )
    work_context_typical: Mapped[WorkContextTypical | None] = mapped_column(
        Enum(
            WorkContextTypical,
            name="work_context_typical",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=True,
    )
    sport_frequency: Mapped[SportFrequency | None] = mapped_column(
        Enum(
            SportFrequency, name="sport_frequency", values_callable=lambda x: [e.value for e in x]
        ),
        nullable=True,
    )
    insight_curiosity: Mapped[InsightCuriosity | None] = mapped_column(
        Enum(
            InsightCuriosity,
            name="insight_curiosity",
            values_callable=lambda x: [e.value for e in x],
        ),
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
