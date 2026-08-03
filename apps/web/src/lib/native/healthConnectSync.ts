/**
 * Foreground Health Connect sleep sync (M8 Sprint 4, #172).
 *
 * Reads sleep sessions via the native bridge, aggregates them into one
 * `sleep_minutes` total per wake-date, and imports them. Consent is enforced
 * both here and server-side; the server also applies the per-field toggle and
 * the manual-wins merge. A native WorkManager background trigger is a documented
 * follow-up — this module is what the in-app "Sync now" action calls.
 */

import type { ConsentListResponse } from '$lib/api/consents';
import { importHealthConnectSleep, type HealthConnectImportResponse } from '$lib/api/healthConnect';
import { canUseHealthConnectImport } from '$lib/healthConnect/consent';
import { canUseOfflineSync } from '$lib/offline/featureFlag';
import { scheduleSync } from '$lib/offline/syncOrchestrator';
import { fillLocalSleepAfterHealthConnectImport } from '$lib/stores/entriesOffline';
import { readHealthConnectSleepAndHeartRate, type HealthConnectSleepRecord } from './healthConnect';

/** Local ISO date (YYYY-MM-DD) of an instant, in the device's timezone. */
function localIsoDate(iso: string): string | null {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

interface SleepInterval {
  startMs: number;
  endMs: number;
}

/**
 * Resolve a session's real [start, end] instants. Falls back to deriving the
 * start from `endTime - durationMinutes` when `startTime` is missing or
 * unparseable, so overlap detection still works with partial data.
 */
function sessionInterval(record: HealthConnectSleepRecord): SleepInterval | null {
  const endMs = new Date(record.endTime).getTime();
  if (Number.isNaN(endMs)) return null;
  const durationMs = Math.max(0, record.durationMinutes) * 60_000;
  const parsedStartMs = new Date(record.startTime).getTime();
  const startMs =
    !Number.isNaN(parsedStartMs) && parsedStartMs < endMs ? parsedStartMs : endMs - durationMs;
  return { startMs, endMs };
}

/**
 * Aggregate sleep sessions into total sleep minutes per wake-date (the local
 * date the session ended).
 *
 * Overlapping sessions (e.g. duplicate records from multiple Health Connect
 * data origins covering the same period) are merged by real time interval
 * before summing, so they never double-count; only genuinely separate
 * sessions on the same date add together. The total is clamped to a single
 * day (1440 minutes).
 */
export function aggregateSleepByDate(records: HealthConnectSleepRecord[]): Map<string, number> {
  const intervalsByDate = new Map<string, SleepInterval[]>();
  for (const record of records) {
    const date = localIsoDate(record.endTime);
    const interval = sessionInterval(record);
    if (!date || !interval) continue;
    const intervals = intervalsByDate.get(date);
    if (intervals) {
      intervals.push(interval);
    } else {
      intervalsByDate.set(date, [interval]);
    }
  }

  const totals = new Map<string, number>();
  for (const [date, intervals] of intervalsByDate) {
    intervals.sort((a, b) => a.startMs - b.startMs);
    let mergedMinutes = 0;
    let { startMs: curStart, endMs: curEnd } = intervals[0];
    for (let i = 1; i < intervals.length; i++) {
      const iv = intervals[i];
      if (iv.startMs <= curEnd) {
        curEnd = Math.max(curEnd, iv.endMs);
      } else {
        mergedMinutes += (curEnd - curStart) / 60_000;
        curStart = iv.startMs;
        curEnd = iv.endMs;
      }
    }
    mergedMinutes += (curEnd - curStart) / 60_000;
    totals.set(date, Math.min(1440, Math.max(0, Math.round(mergedMinutes))));
  }
  return totals;
}

export interface HealthConnectSyncResult {
  status: 'ok' | 'no_consent' | 'unavailable' | 'no_data' | 'sync_disabled';
  imported?: HealthConnectImportResponse;
}

/**
 * Read HC sleep for [start, end], aggregate per wake-date, and import. `start`
 * and `end` are ISO-8601 instants.
 */
export async function syncHealthConnectSleep(
  consents: ConsentListResponse | null | undefined,
  range: { start: string; end: string }
): Promise<HealthConnectSyncResult> {
  if (!canUseHealthConnectImport(consents)) return { status: 'no_consent' };

  const data = await readHealthConnectSleepAndHeartRate(consents, range);
  if (data === null) return { status: 'unavailable' };

  const byDate = aggregateSleepByDate(data.sleep);
  if (byDate.size === 0) return { status: 'no_data' };

  const sleep = [...byDate.entries()].map(([entry_date, sleep_minutes]) => ({
    entry_date,
    sleep_minutes,
  }));
  const imported = await importHealthConnectSleep(sleep);
  // The server is authoritative for the toggle: it may have been disabled on
  // another device, or the client's optimistic preference fetch may be stale.
  // Report that explicitly instead of claiming success when nothing synced.
  if (!imported.sleep_sync_enabled) {
    return { status: 'sync_disabled', imported };
  }
  // Revisions alone are not enough: Sync now must reconcile Dexie (and any
  // pending outbox null sleep) before an offline/API-down mood edit can push
  // nulls and wipe the wearable fill. Also reconcile when the server already
  // held the value (`skipped_existing_value`) so a prior failed local fill can
  // recover on retry (#640).
  const needsLocalReconcile = imported.updated > 0 || imported.skipped_existing_value > 0;
  if (needsLocalReconcile) {
    try {
      await fillLocalSleepAfterHealthConnectImport(sleep, {
        // Intentional-clear protection is only valid on skipped_existing dates.
        skippedExistingDates: imported.skipped_existing_entry_dates ?? [],
      });
    } catch {
      // Best-effort; empty/unopened Dexie is fine. scheduleSync still helps
      // when offline sync is active.
    }
    if (canUseOfflineSync()) {
      scheduleSync();
    }
  }
  return { status: 'ok', imported };
}
