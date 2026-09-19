/**
 * Calendar date helpers (ISO YYYY-MM-DD in local time).
 *
 * Extracted from the former streak module so date math no longer lives
 * under a gamification-named file (Phase 1 / #928).
 */

/** Local-time ISO date (YYYY-MM-DD), free of TZ-offset bugs of toISOString. */
export function localIsoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/**
 * Step `iso` by `deltaDays` calendar days. Pure date math — constructs at
 * noon to dodge DST edge-cases. Returns the shifted ISO date, or `iso`
 * unchanged when the input is not parseable.
 */
export function shiftIsoDate(iso: string, deltaDays: number): string {
  const d = new Date(iso + 'T12:00:00');
  if (Number.isNaN(d.getTime())) return iso;
  d.setDate(d.getDate() + deltaDays);
  return localIsoDate(d);
}
