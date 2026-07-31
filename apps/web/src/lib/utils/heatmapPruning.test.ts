import { describe, expect, it } from 'vitest';
import {
  clampCooccurrenceVisibleCount,
  defaultCooccurrenceVisibleCount,
  pruneHeatmapAxes,
  pruneHeatmapDates,
  pruneHeatmapRows,
  pruneHeatmapRowsByBuckets,
  pruneCooccurrenceAxisIds,
  pruneTagCooccurrenceMatrix,
  sliceAxisIdsByTopStrength,
  sliceSquareMatrixByTopStrength,
} from './heatmapPruning';

describe('heatmapPruning', () => {
  const rows = [
    {
      id: 'a',
      days: [
        { date: '2026-07-01', count: 2 },
        { date: '2026-07-03', count: 0 },
      ],
    },
    {
      id: 'b',
      days: [
        { date: '2026-07-01', count: 0 },
        { date: '2026-07-03', count: 0 },
      ],
    },
  ];
  const dates = ['2026-07-01', '2026-07-02', '2026-07-03'];
  const valueFor = (row: (typeof rows)[number], date: string) =>
    row.days.find((day) => day.date === date)?.count ?? 0;

  it('prunes empty rows', () => {
    expect(pruneHeatmapRows(rows, dates, valueFor).map((row) => row.id)).toEqual(['a']);
  });

  it('prunes rows with no values in visible buckets (#590)', () => {
    type Bucket = { dates: string[] };
    const buckets: Bucket[] = [
      { dates: ['2026-07-02'] },
      { dates: ['2026-07-03'] },
    ];
    const valueForBucket = (row: (typeof rows)[number], bucket: Bucket) =>
      bucket.dates.reduce((sum, date) => sum + valueFor(row, date), 0);

    expect(pruneHeatmapRowsByBuckets(rows, buckets, valueForBucket).map((row) => row.id)).toEqual(
      []
    );
    expect(
      pruneHeatmapRowsByBuckets(rows, [{ dates: ['2026-07-01'] }], valueForBucket).map(
        (row) => row.id
      )
    ).toEqual(['a']);
  });

  it('prunes empty date columns', () => {
    expect(pruneHeatmapDates(rows, dates, valueFor)).toEqual(['2026-07-01']);
  });

  it('prunes rows and dates together', () => {
    expect(pruneHeatmapAxes(rows, dates, valueFor)).toEqual({
      rows: [rows[0]],
      dates: ['2026-07-01'],
    });
  });

  it('prunes tag co-occurrence axes with no pairs', () => {
    const tags = [
      { tag_id: 't1', name: 'Run' },
      { tag_id: 't2', name: 'Sleep' },
      { tag_id: 't3', name: 'Coffee' },
    ];
    const counts = [
      [0, 2, 0],
      [2, 0, 0],
      [0, 0, 0],
    ];
    const pruned = pruneTagCooccurrenceMatrix(tags, counts);
    expect(pruned.tags.map((tag) => tag.tag_id)).toEqual(['t1', 't2']);
    expect(pruned.counts).toEqual([
      [0, 2],
      [2, 0],
    ]);
  });

  it('keeps co-occurrence axes with any positive jaccard profile (#590)', () => {
    const profiles = new Map<string, number[]>([
      ['sym-1', [0.5]],
      ['tag-1', [0.5]],
      ['empty', [0]],
    ]);
    expect(pruneCooccurrenceAxisIds(['sym-1', 'tag-1', 'empty'], profiles)).toEqual([
      'sym-1',
      'tag-1',
    ]);
  });

  it('slices square matrix to strongest axes while preserving order', () => {
    const tags = [
      { tag_id: 'weak', name: 'Weak' },
      { tag_id: 'strong', name: 'Strong' },
      { tag_id: 'mid', name: 'Mid' },
    ];
    const counts = [
      [0, 1, 0],
      [1, 0, 5],
      [0, 5, 0],
    ];
    const sliced = sliceSquareMatrixByTopStrength(tags, counts, 2);
    expect(sliced.totalAxes).toBe(3);
    expect(sliced.visibleAxes).toBe(2);
    // Strongest: strong (6), mid (5); preserve original order → strong, mid
    expect(sliced.tags.map((tag) => tag.tag_id)).toEqual(['strong', 'mid']);
    expect(sliced.counts).toEqual([
      [0, 5],
      [5, 0],
    ]);
  });

  it('clamps density defaults for compact viewports', () => {
    expect(defaultCooccurrenceVisibleCount(20, false)).toBe(20);
    expect(defaultCooccurrenceVisibleCount(20, true)).toBe(8);
    expect(defaultCooccurrenceVisibleCount(3, true)).toBe(3);
    expect(clampCooccurrenceVisibleCount(1, 10)).toBe(4);
    expect(clampCooccurrenceVisibleCount(99, 6)).toBe(6);
  });

  it('slices rectangular axis ids by profile strength', () => {
    const profiles = new Map<string, number[]>([
      ['a', [0.1, 0]],
      ['b', [0.9, 0.8]],
      ['c', [0.2, 0.1]],
    ]);
    const sliced = sliceAxisIdsByTopStrength(['a', 'b', 'c'], profiles, 2);
    expect(sliced.ids).toEqual(['b', 'c']);
    expect(sliced.visibleAxes).toBe(2);
  });
});
