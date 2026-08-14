/**
 * Foreground Health Connect sleep sync (M8 Sprint 4, #172).
 *
 * Reads sleep sessions via the native bridge, aggregates them into one
 * `sleep_minutes` total per wake-date, and imports them. Consent is enforced
 * both here and server-side; the server also applies the per-field toggle and
 * the manual-wins merge. A native WorkManager background trigger is a documented
 * follow-up — this module is what the in-app "Sync now" action calls.
 */

import { ApiError, NetworkError } from '$lib/api/client';
import type { ConsentListResponse } from '$lib/api/consents';
import { importHealthConnectSleep, type HealthConnectImportResponse } from '$lib/api/healthConnect';
import { canUseHealthConnectImport } from '$lib/healthConnect/consent';
import { canUseOfflineSync } from '$lib/offline/featureFlag';
import { scheduleSync } from '$lib/offline/syncOrchestrator';
import { captureClientException } from '$lib/observability/errorTracking.client';
import { fillLocalSleepAfterHealthConnectImport } from '$lib/stores/entriesOffline';
import { readHealthConnectSleep, type HealthConnectSleepRecord } from './healthConnect';
import {
  _resetHealthConnectSyncLifecycleForTests,
  drainHealthConnectSyncForSessionChange,
  trackHealthConnectSyncInFlight,
} from './healthConnectSyncLifecycle';

export { drainHealthConnectSyncForSessionChange };

/**
 * Identity guard for Sync now. The page supplies the actor id and a live
 * lookup so this module does not import the auth store (avoids a cycle through
 * offline session drain).
 */
export interface HealthConnectSyncAuthGuard {
  actorUserId: string;
  currentUserId: () => string | null | undefined;
}

function actorStillCurrent(auth?: HealthConnectSyncAuthGuard): boolean {
  if (!auth) return true;
  const current = auth.currentUserId();
  return typeof current === 'string' && current === auth.actorUserId;
}

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

export type HealthConnectSyncStatus =
  | 'ok'
  | 'no_consent'
  | 'unavailable'
  | 'no_data'
  | 'sync_disabled'
  | 'no_matching_entries'
  | 'already_up_to_date'
  | 'error_network'
  | 'error_forbidden'
  | 'error_not_found'
  | 'error_unauthorized'
  | 'error_server'
  | 'error';

export interface HealthConnectSyncResult {
  status: HealthConnectSyncStatus;
  imported?: HealthConnectImportResponse;
  /**
   * Wake-dates (YYYY-MM-DD, sorted) for which Health Connect sleep was found and
   * sent. Surfaced so the UI can show which days a sync touched (issue #653 A2).
   * The per-day outcome (newly filled vs. manual kept) is only available in
   * aggregate via `imported`, so this is "sleep found for these days".
   */
  dates?: string[];
}

/** Map thrown API/network failures to a user-facing sync status (no sleep payload). */
export function mapHealthConnectImportError(err: unknown): HealthConnectSyncStatus {
  if (err instanceof NetworkError) return 'error_network';
  if (err instanceof ApiError) {
    if (err.status === 401) return 'error_unauthorized';
    if (err.status === 403) return 'error_forbidden';
    if (err.status === 404) return 'error_not_found';
    if (err.status >= 500) return 'error_server';
    return 'error';
  }
  return 'error';
}

function outcomeAfterImport(imported: HealthConnectImportResponse): HealthConnectSyncStatus {
  if (!imported.sleep_sync_enabled) return 'sync_disabled';
  if (imported.updated > 0) return 'ok';
  if (imported.skipped_existing_value > 0 && imported.skipped_no_entry === 0) {
    return 'already_up_to_date';
  }
  if (imported.skipped_no_entry > 0) return 'no_matching_entries';
  return 'ok';
}

/**
 * Read HC sleep for [start, end], aggregate per wake-date, and import. `start`
 * and `end` are ISO-8601 instants. Known API failures become status codes
 * (never throw) so the UI can show a specific message.
 *
 * When ``auth`` is provided, import/local-fill abort if the authenticated user
 * changes mid-flight (wrong-user wearable write). Session login/logout also
 * await {@link drainHealthConnectSyncForSessionChange} so the native read
 * cannot outlive a credential swap.
 */
export async function syncHealthConnectSleep(
  consents: ConsentListResponse | null | undefined,
  range: { start: string; end: string },
  auth?: HealthConnectSyncAuthGuard
): Promise<HealthConnectSyncResult> {
  const run = runHealthConnectSleepSync(consents, range, auth);
  trackHealthConnectSyncInFlight(run);
  return run;
}

/** Test-only: drop in-flight tracking between cases. */
export function _resetHealthConnectSyncForTests(): void {
  _resetHealthConnectSyncLifecycleForTests();
}

async function runHealthConnectSleepSync(
  consents: ConsentListResponse | null | undefined,
  range: { start: string; end: string },
  auth?: HealthConnectSyncAuthGuard
): Promise<HealthConnectSyncResult> {
  if (!canUseHealthConnectImport(consents)) return { status: 'no_consent' };
  if (auth && !actorStillCurrent(auth)) return { status: 'error_unauthorized' };

  const sleepRecords = await readHealthConnectSleep(consents, range);
  if (sleepRecords === null) return { status: 'unavailable' };

  const byDate = aggregateSleepByDate(sleepRecords);
  if (byDate.size === 0) return { status: 'no_data' };

  const sleep = [...byDate.entries()].map(([entry_date, sleep_minutes]) => ({
    entry_date,
    sleep_minutes,
  }));
  const dates = sleep.map((s) => s.entry_date).sort();

  // Re-check after the (slow) native read — login/logout may have swapped the
  // Bearer/cookies. Import uses credentials at request time, so without this
  // guard A's wearable totals would write into B's null-sleep entries.
  if (!actorStillCurrent(auth)) {
    return { status: 'error_unauthorized', dates };
  }

  let imported: HealthConnectImportResponse;
  try {
    imported = await importHealthConnectSleep(sleep);
  } catch (err) {
    const status = mapHealthConnectImportError(err);
    // Scrubbed: status/path only — never the sleep payload.
    captureClientException(
      err instanceof Error ? err : new Error(`health_connect_import_failed:${status}`)
    );
    return { status, dates };
  }

  const status = outcomeAfterImport(imported);
  if (status === 'sync_disabled') {
    return { status, imported, dates };
  }

  // Revisions alone are not enough: Sync now must reconcile Dexie (and any
  // pending outbox null sleep) before an offline/API-down mood edit can push
  // nulls and wipe the wearable fill. Also reconcile when the server already
  // held the value (`skipped_existing_value`) so a prior failed local fill can
  // recover on retry (#640).
  const needsLocalReconcile = imported.updated > 0 || imported.skipped_existing_value > 0;
  if (needsLocalReconcile) {
    if (!actorStillCurrent(auth)) {
      return { status: 'error_unauthorized', imported, dates };
    }
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
  return { status, imported, dates };
}
