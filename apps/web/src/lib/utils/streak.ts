/**
 * Entry-streak helpers — ADR-0014 (M1.5 Home-Dashboard) and ADR-0012.
 *
 * "Entry-Streak" semantics, deliberately *not* "Habit-Streak":
 *  - Counts consecutive days that have a `slot=day` entry, walking
 *    backwards from the reference date (today by default).
 *  - **Coulance for today:** if today has no entry yet, the streak does
 *    not break — we look at yesterday and walk back from there. The
 *    streak only breaks once a *past* day is missing.
 *  - The reference day (today) does not count toward the streak unless
 *    it has its own entry.
 *
 * Pure & deterministic so we can unit-test without the DOM.
 */

import type { EntryResponse } from '$lib/api/entries';

/** Local-time ISO date (YYYY-MM-DD), free of TZ-offset bugs of toISOString. */
export function localIsoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/**
 * Step `iso` one calendar day backward. Pure date math, no Date object
 * mutation leaks. Returns the previous ISO date.
 */
export function shiftIsoDate(iso: string, deltaDays: number): string {
  // Construct at noon to dodge DST edge-cases entirely.
  const d = new Date(iso + 'T12:00:00');
  if (Number.isNaN(d.getTime())) return iso;
  d.setDate(d.getDate() + deltaDays);
  return localIsoDate(d);
}

/**
 * Build a fast Set of ISO dates that have a `slot=day` entry. Other
 * slots are ignored — only the daily entry counts toward the streak.
 */
function dayEntryDateSet(entries: readonly EntryResponse[]): Set<string> {
  const out = new Set<string>();
  for (const e of entries) {
    if (e.slot === 'day') out.add(e.entry_date);
  }
  return out;
}

/**
 * Compute the entry-streak length anchored on `referenceIso` (today).
 *
 * Algorithm:
 *  1. Build the set of day-entry dates from `entries`.
 *  2. If `referenceIso` is in the set, start counting from there.
 *  3. Otherwise, start from `referenceIso - 1 day` (Coulance).
 *  4. Walk backwards day by day; stop at the first missing day.
 *  5. Cap iteration at `entries.length + 1` to avoid runaway loops if
 *     the input ever contained malformed data.
 *
 * Returns the streak length in days. 0 if no consecutive day-entry
 * exists ending at or before `referenceIso`.
 */
export function computeEntryStreak(
  entries: readonly EntryResponse[],
  referenceIso: string
): number {
  const set = dayEntryDateSet(entries);
  if (set.size === 0) return 0;

  let cursor = referenceIso;
  // Coulance: if today is empty, look at yesterday and continue from there.
  if (!set.has(cursor)) {
    cursor = shiftIsoDate(cursor, -1);
  }

  let count = 0;
  // Cap: we only have data for N days, so we can never count higher
  // than N. The +1 is paranoia padding.
  const cap = entries.length + 1;
  while (set.has(cursor) && count < cap) {
    count += 1;
    cursor = shiftIsoDate(cursor, -1);
  }
  return count;
}

/** 7-day simple average for a numeric `EntryResponse` field. */
export function averageOver(
  entries: readonly EntryResponse[],
  field: 'mood_score' | 'energy' | 'stress'
): number | null {
  if (entries.length === 0) return null;
  const dayEntries = entries.filter((e) => e.slot === 'day');
  if (dayEntries.length === 0) return null;
  let sum = 0;
  for (const e of dayEntries) sum += e[field];
  // Round to one decimal to keep the UI clean (3.4 ≠ 3.42857).
  return Math.round((sum / dayEntries.length) * 10) / 10;
}

/** Count of `slot=day` entries in the given list. */
export function countDayEntries(entries: readonly EntryResponse[]): number {
  let n = 0;
  for (const e of entries) if (e.slot === 'day') n += 1;
  return n;
}
