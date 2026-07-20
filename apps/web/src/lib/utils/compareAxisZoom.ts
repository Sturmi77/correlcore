/**
 * Shared-axis display zoom for Trends Compare (CAZ-1).
 * Buckets coarsen the calendar axis without changing the loaded 365d window.
 */

export const COMPARE_ZOOM_STAGES = [1, 3, 7, 14, 28] as const;
export type CompareZoomStageIndex = 0 | 1 | 2 | 3 | 4;

export type AxisBucket = {
  id: string;
  start: string;
  end: string;
  dayCount: number;
  presentDays: number;
  partial: boolean;
  dates: string[];
};

export function stageDays(stage: CompareZoomStageIndex): number {
  return COMPARE_ZOOM_STAGES[stage];
}

export function clampZoomStage(stage: number): CompareZoomStageIndex {
  if (!Number.isFinite(stage)) return 0;
  return Math.max(0, Math.min(4, Math.floor(stage))) as CompareZoomStageIndex;
}

export function isCompareZoomStage(value: unknown): value is CompareZoomStageIndex {
  return value === 0 || value === 1 || value === 2 || value === 3 || value === 4;
}

/**
 * Build display buckets from an oldest→newest ISO date list.
 * Chunks from the newest day backward so the right edge aligns with "today".
 */
export function buildAxisBuckets(
  axisDatesOldestToNewest: readonly string[],
  stage: CompareZoomStageIndex
): AxisBucket[] {
  const dates = [...axisDatesOldestToNewest];
  if (dates.length === 0) return [];

  const size = stageDays(stage);
  if (size <= 1) {
    return dates.map((date) => ({
      id: `${date}_${date}`,
      start: date,
      end: date,
      dayCount: 1,
      presentDays: 1,
      partial: false,
      dates: [date],
    }));
  }

  const bucketsNewestFirst: AxisBucket[] = [];
  let end = dates.length;
  while (end > 0) {
    const start = Math.max(0, end - size);
    const chunk = dates.slice(start, end);
    const first = chunk[0]!;
    const last = chunk[chunk.length - 1]!;
    bucketsNewestFirst.push({
      id: `${first}_${last}`,
      start: first,
      end: last,
      dayCount: size,
      presentDays: chunk.length,
      partial: chunk.length < size,
      dates: chunk,
    });
    end = start;
  }

  return bucketsNewestFirst.reverse();
}

export function sumBucketCounts(
  valueForDate: (date: string) => number,
  bucket: AxisBucket
): number {
  return bucket.dates.reduce((sum, date) => sum + (valueForDate(date) || 0), 0);
}

/** Mean of non-null daily values; empty → null (do not average missing days). */
export function meanBucketMetric(
  valueForDate: (date: string) => number | null | undefined,
  bucket: AxisBucket
): number | null {
  const values: number[] = [];
  for (const date of bucket.dates) {
    const value = valueForDate(date);
    if (typeof value === 'number' && Number.isFinite(value)) {
      values.push(value);
    }
  }
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

/** Count days in the bucket where the daily value is > 0. */
export function countBucketActiveDays(
  valueForDate: (date: string) => number,
  bucket: AxisBucket
): number {
  return bucket.dates.reduce((count, date) => count + (valueForDate(date) > 0 ? 1 : 0), 0);
}

/** Find the display bucket that contains an ISO date (or matches start). */
export function findBucketForDate(
  buckets: readonly AxisBucket[],
  date: string
): AxisBucket | null {
  return (
    buckets.find((bucket) => bucket.dates.includes(date)) ??
    buckets.find((bucket) => bucket.start === date) ??
    null
  );
}

export function formatBucketRangeLabel(bucket: AxisBucket): string {
  return bucket.start === bucket.end ? bucket.start : `${bucket.start} – ${bucket.end}`;
}
