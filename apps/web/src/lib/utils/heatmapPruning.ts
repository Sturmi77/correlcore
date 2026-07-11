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
  profiles: Map<string, number[]>,
  minTotal = 1
): string[] {
  return ids.filter((id) => {
    const profile = profiles.get(id);
    if (!profile) return false;
    const total = profile.reduce((sum, value) => sum + value, 0);
    return total >= minTotal;
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
