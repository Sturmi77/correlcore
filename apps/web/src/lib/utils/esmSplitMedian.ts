/**
 * Split median trajectories — issue #920 (#891 v2, Option 6).
 *
 * v1 showed *that* two events co-occur. Splitting the event windows along the
 * partner turns that into "does the trajectory look different when B is also
 * there": one branch for windows containing the partner, one for the rest.
 *
 * The occurrence floor (#811) applies **per branch** — a branch below it is
 * reported as insufficient rather than drawn, because a median over two
 * windows would look exactly like a finding.
 */

import {
  MIN_SMALL_MULTIPLES_OCCURRENCES,
  SMALL_MULTIPLES_RADIUS,
  hasEnoughOccurrences,
} from '$lib/components/trends/smallMultiplesGate';
import { partnerDatesInWindow } from '$lib/utils/esmPartner';
import {
  buildMedianTrajectory,
  type MedianTrajectoryCell,
  type TrajectorySourceRow,
} from '$lib/utils/medianTrajectory';

export type SplitSourceRow = TrajectorySourceRow & { onset: string };

export type SplitBranchKey = 'with' | 'without';

export type EsmSplitBranch = {
  key: SplitBranchKey;
  /** Windows that fell into this branch — the denominator users see. */
  windows: number;
  /** Median cells, or null when the branch is below the occurrence floor. */
  cells: MedianTrajectoryCell[] | null;
};

export type EsmSplitMedians = {
  withPartner: EsmSplitBranch;
  withoutPartner: EsmSplitBranch;
};

/**
 * A window belongs to the "with" branch when the partner appears anywhere in
 * it — the same ±radius window the cells already render, so the split matches
 * what the user sees marked.
 */
export function splitRowsByPartner<Row extends SplitSourceRow>(
  rows: readonly Row[],
  presenceDates: ReadonlySet<string> | readonly string[],
  radius = SMALL_MULTIPLES_RADIUS
): { withPartner: Row[]; withoutPartner: Row[] } {
  const present = presenceDates instanceof Set ? presenceDates : new Set(presenceDates);
  const withPartner: Row[] = [];
  const withoutPartner: Row[] = [];
  for (const row of rows) {
    if (partnerDatesInWindow(row.onset, present, radius).length > 0) {
      withPartner.push(row);
    } else {
      withoutPartner.push(row);
    }
  }
  return { withPartner, withoutPartner };
}

function buildBranch<Row extends SplitSourceRow>(
  key: SplitBranchKey,
  rows: readonly Row[],
  radius: number
): EsmSplitBranch {
  return {
    key,
    windows: rows.length,
    cells: hasEnoughOccurrences(rows.length) ? buildMedianTrajectory(rows, radius) : null,
  };
}

export function buildSplitMedianTrajectories<Row extends SplitSourceRow>(
  rows: readonly Row[],
  presenceDates: ReadonlySet<string> | readonly string[],
  radius = SMALL_MULTIPLES_RADIUS
): EsmSplitMedians {
  const { withPartner, withoutPartner } = splitRowsByPartner(rows, presenceDates, radius);
  return {
    withPartner: buildBranch('with', withPartner, radius),
    withoutPartner: buildBranch('without', withoutPartner, radius),
  };
}

export { MIN_SMALL_MULTIPLES_OCCURRENCES };
