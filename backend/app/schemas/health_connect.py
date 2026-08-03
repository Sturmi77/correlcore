"""Schemas for the Health Connect import endpoint (M8 Sprint 4, #172).

The import is intentionally sleep-only: it fills ``sleep_minutes`` on existing
entries and never fabricates mood/energy/stress. Heart-rate is read at the
permission level (Sprint 3) but has no entry column yet, so it is not accepted
here — that keeps the "sleep only" write limit technically enforced.
"""

from __future__ import annotations

from datetime import date as date_type

from pydantic import BaseModel, Field

# One year of nightly records is a generous single-request cap.
MAX_IMPORT_ITEMS = 370


class HealthConnectSleepImportItem(BaseModel):
    """A single day's imported sleep duration (attributed by the client)."""

    entry_date: date_type
    sleep_minutes: int = Field(ge=0, le=1440)


class HealthConnectImportRequest(BaseModel):
    """``POST /api/v1/health-connect/import`` body."""

    sleep: list[HealthConnectSleepImportItem] = Field(
        default_factory=list, max_length=MAX_IMPORT_ITEMS
    )


class HealthConnectImportResponse(BaseModel):
    """Summary of what the import merged (manual values always win)."""

    updated: int = Field(ge=0, description="Entries whose empty sleep_minutes was filled")
    skipped_existing_value: int = Field(
        ge=0, description="Entries that already had a sleep value (manual wins)"
    )
    skipped_no_entry: int = Field(
        ge=0, description="Days with no logged entry — not created (mood is required)"
    )
    sleep_sync_enabled: bool = Field(
        description="False when the user disabled the per-field HC sleep toggle"
    )
    # Per-date outcomes let the client apply intentional-clear guards only on
    # skipped days, while always reconciling Dexie/outbox for freshly updated days
    # (avoids clock-ahead pending mood edits blocking #640 fill).
    updated_entry_dates: list[date_type] = Field(
        default_factory=list,
        description="Dates whose empty sleep_minutes was filled on this import",
    )
    skipped_existing_entry_dates: list[date_type] = Field(
        default_factory=list,
        description="Dates skipped because sleep_minutes was already set",
    )
