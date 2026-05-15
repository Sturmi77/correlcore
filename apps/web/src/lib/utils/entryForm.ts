/** Shared entry-form helpers (route + bottom sheet). */

export function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/**
 * Validate `?date=YYYY-MM-DD` and clamp to the 7-day-back window.
 */
export function resolveInitialDate(today: Date, queryDate: string | null): string {
  if (!queryDate) return isoDate(today);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(queryDate)) return isoDate(today);
  const parsed = new Date(queryDate + 'T00:00:00');
  if (Number.isNaN(parsed.getTime())) return isoDate(today);
  const min = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
  if (parsed > today) return isoDate(today);
  if (parsed < min) return isoDate(today);
  return queryDate;
}
