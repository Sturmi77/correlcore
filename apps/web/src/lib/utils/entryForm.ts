/** Shared entry-form helpers (route + bottom sheet). */

export function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
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
  const upperBound = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
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
