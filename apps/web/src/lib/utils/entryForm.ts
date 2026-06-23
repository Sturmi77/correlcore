/** Shared entry-form helpers (route + bottom sheet). */

export function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function parseCalendarDate(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const parsed = new Date(year, month - 1, day);
  if (
    parsed.getFullYear() !== year ||
    parsed.getMonth() !== month - 1 ||
    parsed.getDate() !== day
  ) {
    return null;
  }
  return parsed;
}

export function isEntryDateEditable(today: Date, entryDate: string): boolean {
  const parsed = parseCalendarDate(entryDate);
  if (!parsed) return false;
  const upperBound = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const lowerBound = new Date(upperBound);
  lowerBound.setDate(lowerBound.getDate() - 7);
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
