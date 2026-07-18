"""Widget summary helpers for the Android Glance homescreen widget (M11)."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime, time, timedelta
from datetime import date as date_type

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry, EntrySlot
from app.schemas.widget import WidgetSummaryResponse

# How far back we look for mood average and time-slot history.
_MOOD_WINDOW_DAYS = 7
_HISTORY_LOOKBACK_DAYS = 28
_HISTORY_LIMIT = 60

# Fallback hour (UTC) when a slot has no usable created_at sample.
_SLOT_DEFAULT_HOUR: dict[EntrySlot, int] = {
    EntrySlot.MORNING: 8,
    EntrySlot.NOON: 12,
    EntrySlot.EVENING: 18,
    EntrySlot.DAY: 19,
}

_DEFAULT_SUGGEST_HOUR = 19


def _suggest_hour_from_history(
    rows: list[tuple[datetime, EntrySlot]],
) -> int | None:
    """Return the modal creation hour (UTC) from recent entries, or None."""

    if not rows:
        return None

    hours: list[int] = []
    for created_at, slot in rows:
        if created_at is not None:
            ts = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
            hours.append(ts.astimezone(UTC).hour)
        else:
            hours.append(_SLOT_DEFAULT_HOUR.get(slot, _DEFAULT_SUGGEST_HOUR))

    if not hours:
        return None

    # Most common hour; ties broken by earliest hour (stable, predictable).
    counts = Counter(hours)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _next_suggested_at(
    *,
    now: datetime,
    has_entry_today: bool,
    suggest_hour: int | None,
) -> datetime | None:
    if suggest_hour is None:
        return None

    today = now.astimezone(UTC).date()
    candidate = datetime.combine(today, time(hour=suggest_hour, minute=0), tzinfo=UTC)
    if has_entry_today or candidate <= now:
        candidate += timedelta(days=1)
    return candidate


async def get_widget_summary(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
) -> WidgetSummaryResponse:
    """Build a ≤1 KB summary for frequent widget polling."""

    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    else:
        now = now.astimezone(UTC)

    today: date_type = now.date()
    mood_start = today - timedelta(days=_MOOD_WINDOW_DAYS - 1)
    history_start = today - timedelta(days=_HISTORY_LOOKBACK_DAYS)

    has_entry_result = await db.execute(
        select(func.count())
        .select_from(Entry)
        .where(Entry.user_id == user_id, Entry.entry_date == today)
    )
    has_entry = int(has_entry_result.scalar_one() or 0) > 0

    mood_result = await db.execute(
        select(func.avg(Entry.mood_score)).where(
            Entry.user_id == user_id,
            Entry.entry_date >= mood_start,
            Entry.entry_date <= today,
        )
    )
    mood_raw = mood_result.scalar_one()
    mood_avg_7d = round(float(mood_raw), 2) if mood_raw is not None else None

    history_result = await db.execute(
        select(Entry.created_at, Entry.slot)
        .where(
            Entry.user_id == user_id,
            Entry.entry_date >= history_start,
            Entry.entry_date <= today,
        )
        .order_by(Entry.created_at.desc())
        .limit(_HISTORY_LIMIT)
    )
    history_rows = [(row[0], row[1]) for row in history_result.all()]
    suggest_hour = _suggest_hour_from_history(history_rows)
    if suggest_hour is None and not has_entry:
        suggest_hour = _DEFAULT_SUGGEST_HOUR

    return WidgetSummaryResponse(
        has_entry=has_entry,
        mood_avg_7d=mood_avg_7d,
        suggested_next_entry_at=_next_suggested_at(
            now=now,
            has_entry_today=has_entry,
            suggest_hour=suggest_hour,
        ),
    )
