/**
 * Compare coincidence (A∩B) — issue #908 / ADR-0035 addendum.
 *
 * Derives soft-band marker candidates from pinned heatmap rows already loaded
 * on the client. No worker, no insight type, no statistics — presence only.
 */

import type { EventMarker } from '$lib/components/trends/EventMarkerLayer.svelte';

/** Minimum shared days before the highlight toggle may turn on (honest empty). */
export const MIN_COINCIDENCE_DAYS = 2;

/** Pin budget on Compare (ADR-0035 / M3.8); unchanged by coincidence. */
export const MAX_COMPARE_PINS = 3;

export type CoincidenceRowDay = {
  date: string;
  count: number;
  max_intensity?: number;
};

export type CoincidenceRow = {
  id: string;
  label: string;
  days: CoincidenceRowDay[];
};

export type CoincidenceSubject = {
  id: string;
  label: string;
};

export type CoincidenceDay = {
  date: string;
  subjects: CoincidenceSubject[];
};

export type CoincidenceResult = {
  days: CoincidenceDay[];
  /** ≥2 pins resolved and coincidence day count ≥ minDays. */
  canHighlight: boolean;
};

/** A row is active on a day when any presence signal is non-zero. */
export function isRowActiveOnDay(row: CoincidenceRow, date: string): boolean {
  const day = row.days.find((item) => item.date === date);
  if (!day) return false;
  return day.count > 0 || (day.max_intensity ?? 0) > 0;
}

/**
 * Days where at least two pinned rows are jointly active (A∩B…∩C).
 * Pin order is preserved in `subjects`.
 */
export function deriveCoincidence(
  pinnedIds: readonly string[],
  rows: readonly CoincidenceRow[],
  options?: { minDays?: number }
): CoincidenceResult {
  const minDays = options?.minDays ?? MIN_COINCIDENCE_DAYS;
  const byId = new Map(rows.map((row) => [row.id, row]));
  const pinnedRows = pinnedIds
    .map((id) => byId.get(id))
    .filter((row): row is CoincidenceRow => row != null);

  if (pinnedRows.length < 2) {
    return { days: [], canHighlight: false };
  }

  const dateSet = new Set<string>();
  for (const row of pinnedRows) {
    for (const day of row.days) {
      if (isRowActiveOnDay(row, day.date)) dateSet.add(day.date);
    }
  }

  const days: CoincidenceDay[] = [];
  for (const date of [...dateSet].sort()) {
    const subjects = pinnedRows
      .filter((row) => isRowActiveOnDay(row, date))
      .map((row) => ({ id: row.id, label: row.label }));
    if (subjects.length >= 2) {
      days.push({ date, subjects });
    }
  }

  return {
    days,
    canHighlight: days.length >= minDays,
  };
}

/**
 * Build EventMarker soft bands (endDate set → band in EventMarkerLayer).
 * `labelFor` / `description` come from i18n in the caller.
 */
export function coincidenceDaysToMarkers(
  days: readonly CoincidenceDay[],
  labelFor: (subjectLabels: readonly string[]) => string,
  description?: string
): EventMarker[] {
  return days.map((day) => ({
    date: day.date,
    endDate: day.date,
    kind: 'generic' as const,
    label: labelFor(day.subjects.map((subject) => subject.label)),
    ...(description ? { description } : {}),
  }));
}

/** Clamp pin list to MAX_COMPARE_PINS, dropping extras from the end. */
export function clampPinnedIds(pinnedIds: readonly string[]): string[] {
  return pinnedIds.slice(0, MAX_COMPARE_PINS);
}

export function canPinMore(pinnedCount: number): boolean {
  return pinnedCount < MAX_COMPARE_PINS;
}
