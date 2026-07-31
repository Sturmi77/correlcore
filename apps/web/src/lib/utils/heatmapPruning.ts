export type HeatmapPrunableRow = {
  id: string;
  days: readonly { date: string; count?: number; max_intensity?: number }[];
};

export function rowValueForDate(
  row: HeatmapPrunableRow,
  date: string,
  kind: 'tag' | 'symptom' | 'work_context' = 'tag'
): number {
  const day = row.days.find((item) => item.date === date);
  if (!day) return 0;
  if (kind === 'symptom') return day.max_intensity ?? day.count ?? 0;
  return day.count ?? 0;
}

export function pruneHeatmapRows<T extends HeatmapPrunableRow>(
  rows: readonly T[],
  dates: readonly string[],
  valueFor: (row: T, date: string) => number
): T[] {
  if (dates.length === 0) return [...rows];
  return rows.filter((row) => dates.some((date) => valueFor(row, date) > 0));
}

/** Hide rows with zero values across all visible Compare zoom buckets (O-59 / #590). */
export function pruneHeatmapRowsByBuckets<T, B>(
  rows: readonly T[],
  buckets: readonly B[],
  valueForBucket: (row: T, bucket: B) => number
): T[] {
  if (buckets.length === 0) return [...rows];
  return rows.filter((row) => buckets.some((bucket) => valueForBucket(row, bucket) > 0));
}

export function pruneHeatmapDates<T extends HeatmapPrunableRow>(
  rows: readonly T[],
  dates: readonly string[],
  valueFor: (row: T, date: string) => number
): string[] {
  if (rows.length === 0) return [...dates];
  return dates.filter((date) => rows.some((row) => valueFor(row, date) > 0));
}

export function pruneHeatmapAxes<T extends HeatmapPrunableRow>(
  rows: readonly T[],
  dates: readonly string[],
  valueFor: (row: T, date: string) => number
): { rows: T[]; dates: string[] } {
  const activeDates = pruneHeatmapDates(rows, dates, valueFor);
  const activeRows = pruneHeatmapRows(rows, activeDates, valueFor);
  return { rows: activeRows, dates: activeDates };
}

export function pruneCooccurrenceAxisIds(
  ids: readonly string[],
  profiles: Map<string, number[]>
): string[] {
  return ids.filter((id) => {
    const profile = profiles.get(id);
    if (!profile) return false;
    return profile.some((value) => value > 0);
  });
}

export function pruneTagCooccurrenceMatrix<T extends { tag_id: string }>(
  tags: readonly T[],
  counts: readonly (readonly number[])[]
): { tags: T[]; counts: number[][] } {
  const activeIndexes = tags
    .map((tag, index) => {
      const row = counts[index] ?? [];
      const rowSum = row.reduce((sum, value) => sum + value, 0);
      const colSum = counts.reduce((sum, col) => sum + (col[index] ?? 0), 0);
      return rowSum + colSum > 0 ? index : -1;
    })
    .filter((index) => index >= 0);

  const prunedTags = activeIndexes.map((index) => tags[index]!);
  const prunedCounts = activeIndexes.map((rowIndex) =>
    activeIndexes.map((colIndex) => counts[rowIndex]?.[colIndex] ?? 0)
  );
  return { tags: prunedTags, counts: prunedCounts };
}

/** Minimum axes kept when collapsing a co-occurrence matrix via density controls. */
export const COOCCURRENCE_MIN_VISIBLE = 4;
/** Compact (mobile) default when the matrix has many axes. */
export const COOCCURRENCE_MOBILE_DEFAULT_VISIBLE = 8;

export function clampCooccurrenceVisibleCount(visibleCount: number, total: number): number {
  if (total <= 0) return 0;
  const minVisible = Math.min(COOCCURRENCE_MIN_VISIBLE, total);
  return Math.max(minVisible, Math.min(total, Math.floor(visibleCount)));
}

export function defaultCooccurrenceVisibleCount(total: number, compact: boolean): number {
  if (total <= 0) return 0;
  if (!compact) return total;
  return clampCooccurrenceVisibleCount(Math.min(COOCCURRENCE_MOBILE_DEFAULT_VISIBLE, total), total);
}

export function squareMatrixAxisStrength(
  counts: readonly (readonly number[])[],
  index: number
): number {
  const row = counts[index] ?? [];
  return row.reduce((sum, value, colIndex) => (colIndex === index ? sum : sum + value), 0);
}

function clampVisibleAxisCount(visibleCount: number, total: number): number {
  if (total <= 0) return 0;
  return Math.max(1, Math.min(total, Math.floor(visibleCount)));
}

/**
 * Keep the strongest axes by overlap sum while preserving the current axis order
 * (alphabetical / cluster order from the caller).
 */
export function sliceSquareMatrixByTopStrength<T>(
  tags: readonly T[],
  counts: readonly (readonly number[])[],
  visibleCount: number
): { tags: T[]; counts: number[][]; totalAxes: number; visibleAxes: number } {
  const totalAxes = tags.length;
  if (totalAxes === 0) {
    return { tags: [], counts: [], totalAxes: 0, visibleAxes: 0 };
  }

  const keep = clampVisibleAxisCount(visibleCount, totalAxes);
  if (keep >= totalAxes) {
    return {
      tags: [...tags],
      counts: counts.map((row) => [...row]),
      totalAxes,
      visibleAxes: totalAxes,
    };
  }

  const ranked = tags
    .map((_, index) => ({ index, strength: squareMatrixAxisStrength(counts, index) }))
    .sort((a, b) => b.strength - a.strength || a.index - b.index)
    .slice(0, keep)
    .map((item) => item.index);

  const keepSet = new Set(ranked);
  const activeIndexes = tags.map((_, index) => index).filter((index) => keepSet.has(index));
  return {
    tags: activeIndexes.map((index) => tags[index]!),
    counts: activeIndexes.map((rowIndex) =>
      activeIndexes.map((colIndex) => counts[rowIndex]?.[colIndex] ?? 0)
    ),
    totalAxes,
    visibleAxes: activeIndexes.length,
  };
}

export function profileAxisStrength(profile: readonly number[] | undefined): number {
  if (!profile) return 0;
  return profile.reduce((sum, value) => sum + value, 0);
}

/**
 * Keep the strongest axis ids by profile sum while preserving caller order.
 */
export function sliceAxisIdsByTopStrength(
  ids: readonly string[],
  profiles: Map<string, number[]>,
  visibleCount: number
): { ids: string[]; totalAxes: number; visibleAxes: number } {
  const totalAxes = ids.length;
  if (totalAxes === 0) {
    return { ids: [], totalAxes: 0, visibleAxes: 0 };
  }

  const keep = clampVisibleAxisCount(visibleCount, totalAxes);
  if (keep >= totalAxes) {
    return { ids: [...ids], totalAxes, visibleAxes: totalAxes };
  }

  const ranked = ids
    .map((id, index) => ({
      id,
      index,
      strength: profileAxisStrength(profiles.get(id)),
    }))
    .sort((a, b) => b.strength - a.strength || a.index - b.index)
    .slice(0, keep)
    .map((item) => item.id);

  const keepSet = new Set(ranked);
  const kept = ids.filter((id) => keepSet.has(id));
  return { ids: kept, totalAxes, visibleAxes: kept.length };
}
