import { describe, expect, it } from 'vitest';
import {
  buildAxisBuckets,
  clampZoomStage,
  meanBucketMetric,
  stageDays,
  sumBucketCounts,
  type AxisBucket,
} from './compareAxisZoom';

function isoRange(start: string, count: number): string[] {
  const out: string[] = [];
  const cursor = new Date(`${start}T12:00:00`);
  for (let i = 0; i < count; i += 1) {
    const year = cursor.getFullYear();
    const month = String(cursor.getMonth() + 1).padStart(2, '0');
    const day = String(cursor.getDate()).padStart(2, '0');
    out.push(`${year}-${month}-${day}`);
    cursor.setDate(cursor.getDate() + 1);
  }
  return out;
}

describe('compareAxisZoom', () => {
  it('maps stage index to day counts', () => {
    expect(stageDays(0)).toBe(1);
    expect(stageDays(2)).toBe(7);
    expect(stageDays(4)).toBe(28);
  });

  it('clamps zoom stage to 0..4', () => {
    expect(clampZoomStage(-1)).toBe(0);
    expect(clampZoomStage(9)).toBe(4);
    expect(clampZoomStage(2.9)).toBe(2);
  });

  it('builds one bucket per day at stage 0', () => {
    const dates = isoRange('2026-05-01', 5);
    const buckets = buildAxisBuckets(dates, 0);
    expect(buckets).toHaveLength(5);
    expect(buckets.every((bucket) => bucket.dayCount === 1 && !bucket.partial)).toBe(true);
    expect(buckets[0]?.start).toBe('2026-05-01');
    expect(buckets[4]?.end).toBe('2026-05-05');
  });

  it('splits 28 days into four full week buckets at stage 7', () => {
    const dates = isoRange('2026-01-01', 28);
    const buckets = buildAxisBuckets(dates, 2);
    expect(buckets).toHaveLength(4);
    expect(buckets.every((bucket) => bucket.presentDays === 7 && !bucket.partial)).toBe(true);
    expect(buckets[buckets.length - 1]?.end).toBe(dates[dates.length - 1]);
  });

  it('puts a partial bucket on the left for 30 days at stage 7', () => {
    const dates = isoRange('2026-01-01', 30);
    const buckets = buildAxisBuckets(dates, 2);
    expect(buckets).toHaveLength(5);
    expect(buckets[0]?.presentDays).toBe(2);
    expect(buckets[0]?.partial).toBe(true);
    expect(buckets.slice(1).every((bucket) => bucket.presentDays === 7 && !bucket.partial)).toBe(
      true
    );
    expect(buckets[buckets.length - 1]?.end).toBe(dates[dates.length - 1]);
  });

  it('sums sparse daily counts across a bucket', () => {
    const bucket: AxisBucket = {
      id: 'a_b',
      start: '2026-05-01',
      end: '2026-05-03',
      dayCount: 3,
      presentDays: 3,
      partial: false,
      dates: ['2026-05-01', '2026-05-02', '2026-05-03'],
    };
    const values: Record<string, number> = {
      '2026-05-01': 2,
      '2026-05-03': 1,
    };
    expect(sumBucketCounts((date) => values[date] ?? 0, bucket)).toBe(3);
  });

  it('means only days with finite values', () => {
    const bucket: AxisBucket = {
      id: 'a_b',
      start: '2026-05-01',
      end: '2026-05-03',
      dayCount: 3,
      presentDays: 3,
      partial: false,
      dates: ['2026-05-01', '2026-05-02', '2026-05-03'],
    };
    expect(
      meanBucketMetric((date) => {
        if (date === '2026-05-01') return 2;
        if (date === '2026-05-02') return null;
        return 4;
      }, bucket)
    ).toBe(3);
    expect(meanBucketMetric(() => null, bucket)).toBeNull();
  });
});
