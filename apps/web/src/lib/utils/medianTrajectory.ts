/**
 * Median (+ IQR) trajectory across event-aligned windows (#810 / ADR-0035 §6).
 *
 * For each offset in −radius…+radius, takes the display values from every
 * episode row (nulls excluded) and returns the median plus quartiles.
 * Callers must gate rendering with `hasEnoughOccurrences` (#811).
 */

export type TrajectorySourceCell = {
  offset: number;
  displayValue: number | null;
};

export type TrajectorySourceRow = {
  cells: readonly TrajectorySourceCell[];
};

export type MedianTrajectoryCell = {
  offset: number;
  /** Median display value, or null when no row has a value at this offset. */
  median: number | null;
  q1: number | null;
  q3: number | null;
  /** Number of finite values that contributed. */
  n: number;
};

function sortedFinite(values: readonly (number | null | undefined)[]): number[] {
  return values
    .filter((v): v is number => typeof v === 'number' && Number.isFinite(v))
    .sort((a, b) => a - b);
}

/** Arithmetic median of a non-empty ascending array. */
export function medianOfSorted(sorted: readonly number[]): number {
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}

/** Linear-interpolation quantile for q in [0, 1] on a non-empty ascending array. */
export function quantileOfSorted(sorted: readonly number[], q: number): number {
  if (sorted.length === 1) return sorted[0];
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  const next = sorted[Math.min(base + 1, sorted.length - 1)];
  return sorted[base] + (next - sorted[base]) * rest;
}

export function buildMedianTrajectory(
  rows: readonly TrajectorySourceRow[],
  radius: number
): MedianTrajectoryCell[] {
  const cells: MedianTrajectoryCell[] = [];
  for (let offset = -radius; offset <= radius; offset += 1) {
    const values = sortedFinite(
      rows.map((row) => row.cells.find((cell) => cell.offset === offset)?.displayValue ?? null)
    );
    if (values.length === 0) {
      cells.push({ offset, median: null, q1: null, q3: null, n: 0 });
      continue;
    }
    cells.push({
      offset,
      median: medianOfSorted(values),
      q1: quantileOfSorted(values, 0.25),
      q3: quantileOfSorted(values, 0.75),
      n: values.length,
    });
  }
  return cells;
}
