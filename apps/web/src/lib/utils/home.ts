/**
 * Home-Screen helpers — Issue #97, M3.5 Sprint 4 (ADR-0017).
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
    if (e.entry_date === isoDay && e.slot === 'day') return e;
  }
  return null;
}

/** Locale-aware long date for the home header (e.g. "Wednesday, 15 May"). */
export function formatHomeDate(iso: string, locale: string): string {
  const parsed = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(parsed.getTime())) return iso;
  return new Intl.DateTimeFormat(locale, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(parsed);
}
