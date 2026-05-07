/**
 * Home-Screen helpers — Issue #97.
 *
 * Pure, side-effect-free utilities used by the authenticated Home view.
 * Extracted from the route component so they can be unit-tested without a
 * Svelte component-testing harness (we currently only ship store/util tests).
 */

import type { EntryResponse } from '$lib/api/entries';

/** ISO date in local time (YYYY-MM-DD). Avoids the TZ shift of toISOString(). */
export function localIsoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/**
 * Pick the time-of-day greeting i18n key.
 *   05:00–11:59 → morning
 *   18:00–04:59 → evening
 *   otherwise   → day (generic "Hallo")
 */
export function greetingKey(
  hour: number
): 'home.greeting_morning' | 'home.greeting_day' | 'home.greeting_evening' {
  if (hour >= 5 && hour < 12) return 'home.greeting_morning';
  if (hour >= 18 || hour < 5) return 'home.greeting_evening';
  return 'home.greeting_day';
}

/** Find an entry whose entry_date matches the given ISO date, if any. */
export function findEntryForDate(
  entries: readonly EntryResponse[] | null | undefined,
  isoDay: string
): EntryResponse | null {
  if (!entries || entries.length === 0) return null;
  for (const e of entries) {
    if (e.entry_date === isoDay) return e;
  }
  return null;
}
