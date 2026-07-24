/** Shared entry-form helpers (route + bottom sheet). */

/**
 * Calendar date in device-local time (`YYYY-MM-DD`).
 *
 * Entry rows are keyed by the client's local day (same convention as
 * `localIsoDate` on Home and the widget `tz` query). Do not use
 * `toISOString()` here — after local evening in the Americas that yields
 * UTC tomorrow and the form silently writes the wrong `entry_date`.
 */
export function isoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

const DAY_MS = 24 * 60 * 60 * 1000;

function parseCalendarDate(value: string): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  if (
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() !== month - 1 ||
    parsed.getUTCDate() !== day
  ) {
    return null;
  }
  return parsed.getTime();
}

export function isEntryDateEditable(today: Date, entryDate: string): boolean {
  const parsed = parseCalendarDate(entryDate);
  if (!parsed) return false;
  // Bound the editable window with the same local calendar day as isoDate.
  const upperBound = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  const lowerBound = upperBound - 7 * DAY_MS;
  return parsed >= lowerBound && parsed <= upperBound;
}

/**
 * Validate `?date=YYYY-MM-DD` and clamp to the 7-day-back window.
 */
export function resolveInitialDate(today: Date, queryDate: string | null): string {
  if (!queryDate) return isoDate(today);
  if (!isEntryDateEditable(today, queryDate)) return isoDate(today);
  return queryDate;
}
