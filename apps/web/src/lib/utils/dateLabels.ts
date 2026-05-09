/**
 * Localised date labels for the home dashboard cards (ADR-0014).
 *
 * Returns one of three classes:
 *  - { kind: 'today' }
 *  - { kind: 'yesterday' }
 *  - { kind: 'weekday', weekdayIso }   — short weekday key, e.g. 'mon'
 *
 * Translation happens in the component via i18n; this util is purely
 * the date-math classifier so it stays unit-testable.
 */

import { localIsoDate, shiftIsoDate } from './streak';

export type DateLabelKind =
  | { kind: 'today' }
  | { kind: 'yesterday' }
  | { kind: 'weekday'; weekday: WeekdayKey };

/** ISO weekday short keys — match `home.weekday.<key>` i18n entries. */
export type WeekdayKey = 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun';

const WEEKDAY_KEYS: readonly WeekdayKey[] = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];

export function classifyDateLabel(iso: string, todayIso: string): DateLabelKind {
  if (iso === todayIso) return { kind: 'today' };
  if (iso === shiftIsoDate(todayIso, -1)) return { kind: 'yesterday' };
  // Build a noon-anchored Date so DST shifts can't corrupt the weekday.
  const d = new Date(iso + 'T12:00:00');
  if (Number.isNaN(d.getTime())) return { kind: 'weekday', weekday: 'mon' };
  const wkIdx = d.getDay(); // 0 = Sun
  return { kind: 'weekday', weekday: WEEKDAY_KEYS[wkIdx] };
}

/** Re-export for component sites. */
export { localIsoDate };
