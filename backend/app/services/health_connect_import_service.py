"""Health Connect sleep import (M8 Sprint 4, #172).

Fills ``sleep_minutes`` on existing entries from wearable-recorded sleep, with
two hard rules:

* **Manual wins** — only entries whose ``sleep_minutes`` is currently NULL are
  touched; a value the user typed (or a prior import) is never overwritten.
* **No fabricated entries** — days without a logged entry are skipped, because
  ``mood``/``energy``/``stress`` are required and must not be invented.

Consent (DSGVO Art. 9) is checked at the endpoint; the per-field toggle
``health_connect_sync_sleep_enabled`` is honoured here.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry, EntrySlot
from app.schemas.health_connect import HealthConnectImportResponse, HealthConnectSleepImportItem
from app.services.user_preferences_service import get_or_create_user_preferences

logger = logging.getLogger(__name__)


async def import_health_connect_sleep(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    items: Sequence[HealthConnectSleepImportItem],
) -> HealthConnectImportResponse:
    """Merge wearable sleep durations into existing entries (manual wins)."""

    preferences = await get_or_create_user_preferences(db, user_id=user_id)
    if not preferences.health_connect_sync_sleep_enabled:
        return HealthConnectImportResponse(
            updated=0,
            skipped_existing_value=0,
            skipped_no_entry=len(items),
            sleep_sync_enabled=False,
        )

    updated = 0
    skipped_existing = 0
    skipped_no_entry = 0
    touched: list[Entry] = []

    for item in items:
        result = await db.execute(
            select(Entry).where(
                Entry.user_id == user_id,
                Entry.entry_date == item.entry_date,
                Entry.slot == EntrySlot.DAY,
            )
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            skipped_no_entry += 1
            continue
        if entry.sleep_minutes is not None:
            skipped_existing += 1
            continue
        entry.sleep_minutes = item.sleep_minutes
        updated += 1
        touched.append(entry)

    if touched:
        await db.flush()
        # Emit revisions so offline clients that already advanced their cursor
        # receive the wearable-filled sleep value.
        from app.services.sync_service import record_entry_upsert_revision

        for entry in touched:
            await record_entry_upsert_revision(db, user_id=user_id, entry=entry)

    logger.info(
        "health_connect.sleep_imported",
        extra={"user_id": str(user_id), "updated": updated},
    )
    return HealthConnectImportResponse(
        updated=updated,
        skipped_existing_value=skipped_existing,
        skipped_no_entry=skipped_no_entry,
        sleep_sync_enabled=True,
    )
