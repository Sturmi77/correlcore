/**
 * Compare Lag-1 sequences (A→B +1d) — issue #910 / ADR-0035 addendum.
 *
 * Second marker kind beside same-day coincidence (#908). Marks the day of A
 * when A is active and the next pinned row B is active on the following
 * calendar day. Client-side presence only — no engine, no causal claim.
 */

import type { EventMarker } from '$lib/components/trends/EventMarkerLayer.svelte';
import {
  activeDatesOf,
  isRowActiveOnDay,
  resolvePinnedRows,
  type CoincidenceRow,
  type CoincidenceSubject,
} from '$lib/utils/coincidenceMarkers';
import { shiftIsoDate } from '$lib/utils/streak';

/** Minimum Lag-1 days before the highlight toggle may turn on. */
export const MIN_LAG1_DAYS = 2;

export type Lag1Sequence = {
  from: CoincidenceSubject;
  to: CoincidenceSubject;
};

export type Lag1Day = {
  /** Calendar day of A (the antecedent). */
  date: string;
  sequences: Lag1Sequence[];
};

export type Lag1Result = {
  days: Lag1Day[];
  canHighlight: boolean;
};

/**
 * Adjacent pinned pairs in pin order (A→B, B→C). Day D is marked when the
 * left subject is active on D and the right subject is active on D+1.
 */
export function deriveLag1(
  pinnedIds: readonly string[],
  rows: readonly CoincidenceRow[],
  options?: { minDays?: number }
): Lag1Result {
  const minDays = options?.minDays ?? MIN_LAG1_DAYS;
  const byId = new Map(rows.map((row) => [row.id, row]));
  const pinnedRows = pinnedIds
    .map((id) => byId.get(id))
    .filter((row): row is CoincidenceRow => row != null);

  if (pinnedRows.length < 2) {
    return { days: [], canHighlight: false };
  }

  const byDate = new Map<string, Lag1Sequence[]>();

  for (let index = 0; index < pinnedRows.length - 1; index += 1) {
    const fromRow = pinnedRows[index]!;
    const toRow = pinnedRows[index + 1]!;
    for (const day of fromRow.days) {
      if (!isRowActiveOnDay(fromRow, day.date)) continue;
      const nextDate = shiftIsoDate(day.date, 1);
      if (!isRowActiveOnDay(toRow, nextDate)) continue;
      const sequence: Lag1Sequence = {
        from: { id: fromRow.id, label: fromRow.label },
        to: { id: toRow.id, label: toRow.label },
      };
      const existing = byDate.get(day.date) ?? [];
      if (
        !existing.some((item) => item.from.id === sequence.from.id && item.to.id === sequence.to.id)
      ) {
        existing.push(sequence);
        byDate.set(day.date, existing);
      }
    }
  }

  const days: Lag1Day[] = [...byDate.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([date, sequences]) => ({ date, sequences }));

  return {
    days,
    canHighlight: days.length >= minDays,
  };
}

/** Both directions for one adjacent pinned pair (#917 / v1c). */
export type Lag1PairSummary = {
  from: CoincidenceSubject;
  to: CoincidenceSubject;
  /** Days where `from` is active and `to` follows on the next day. */
  forward: number;
  /** `from` days that had a next day inside the range — the denominator. */
  forwardTotal: number;
  /** The mirrored count — the asymmetry is the point. */
  reverse: number;
  reverseTotal: number;
};

/**
 * Hits plus opportunities. Without the denominator "3 · 2" reads as an
 * asymmetry even when the 3 comes from 100 antecedent days and the 2 from two,
 * so both numbers are counted against the days that could have produced them.
 * A day only counts as an opportunity when its successor is inside the range.
 */
function countNextDay(
  fromDates: ReadonlySet<string>,
  toDates: ReadonlySet<string>,
  axisDates: ReadonlySet<string> | null
): { hits: number; total: number } {
  let hits = 0;
  let total = 0;
  for (const date of fromDates) {
    const nextDate = shiftIsoDate(date, 1);
    if (axisDates && !axisDates.has(nextDate)) continue;
    total += 1;
    if (toDates.has(nextDate)) hits += 1;
  }
  return { hits, total };
}

/**
 * Counts for the same adjacent pairs `deriveLag1` marks, but in **both**
 * directions. Markers only ever show A→B; without the mirrored count a user
 * cannot tell whether B→A is the more frequent order.
 *
 * `axisDates` bounds the opportunity count to the rendered range; omit it and
 * every active day counts as an opportunity.
 */
export function summarizeLag1(
  pinnedIds: readonly string[],
  rows: readonly CoincidenceRow[],
  options?: { axisDates?: readonly string[] }
): Lag1PairSummary[] {
  const pinnedRows = resolvePinnedRows(pinnedIds, rows);
  if (pinnedRows.length < 2) return [];

  const axisDates = options?.axisDates ? new Set(options.axisDates) : null;
  const activeByRow = pinnedRows.map((row) => activeDatesOf(row));
  const summaries: Lag1PairSummary[] = [];

  for (let index = 0; index < pinnedRows.length - 1; index += 1) {
    const fromRow = pinnedRows[index]!;
    const toRow = pinnedRows[index + 1]!;
    const fromDates = activeByRow[index]!;
    const toDates = activeByRow[index + 1]!;
    const forward = countNextDay(fromDates, toDates, axisDates);
    const reverse = countNextDay(toDates, fromDates, axisDates);
    summaries.push({
      from: { id: fromRow.id, label: fromRow.label },
      to: { id: toRow.id, label: toRow.label },
      forward: forward.hits,
      forwardTotal: forward.total,
      reverse: reverse.hits,
      reverseTotal: reverse.total,
    });
  }

  return summaries;
}

/**
 * The markers only draw the pin-order direction, so its gate cannot decide
 * whether the numbers are worth showing: a pair whose reverse order dominates
 * would stay invisible. Either direction clearing the floor is enough.
 */
export function hasReportableLag1(
  summaries: readonly Lag1PairSummary[],
  minDays = MIN_LAG1_DAYS
): boolean {
  return summaries.some((pair) => pair.forward >= minDays || pair.reverse >= minDays);
}

/**
 * Narrow Lag-1 markers: dashed line (no endDate) with kind `compare_lag1`
 * so they stay visually distinct from A∩B soft bands.
 */
export function lag1DaysToMarkers(
  days: readonly Lag1Day[],
  labelFor: (from: string, to: string) => string,
  description?: string
): EventMarker[] {
  return days.map((day) => {
    const primary = day.sequences[0]!;
    const label =
      day.sequences.length === 1
        ? labelFor(primary.from.label, primary.to.label)
        : day.sequences.map((seq) => labelFor(seq.from.label, seq.to.label)).join(' · ');
    return {
      date: day.date,
      kind: 'compare_lag1' as const,
      label,
      ...(description ? { description } : {}),
    };
  });
}
