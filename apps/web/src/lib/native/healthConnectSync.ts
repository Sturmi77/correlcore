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

/**
 * Aggregate sleep sessions into total sleep minutes per wake-date (the local
 * date the session ended). Multiple sessions on one date sum; the total is
 * clamped to a single day (1440 minutes).
 */
export function aggregateSleepByDate(records: HealthConnectSleepRecord[]): Map<string, number> {
  const byDate = new Map<string, number>();
  for (const record of records) {
    const date = localIsoDate(record.endTime);
    if (!date) continue;
    const minutes = Math.max(0, Math.round(record.durationMinutes));
    byDate.set(date, Math.min(1440, (byDate.get(date) ?? 0) + minutes));
  }
  return byDate;
}

export interface HealthConnectSyncResult {
  status: 'ok' | 'no_consent' | 'unavailable' | 'no_data';
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
  return { status: 'ok', imported };
}
