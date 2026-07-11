import { describe, expect, it } from 'vitest';
import {
  pruneHeatmapAxes,
  pruneHeatmapDates,
  pruneHeatmapRows,
  pruneTagCooccurrenceMatrix,
} from './heatmapPruning';

describe('heatmapPruning', () => {
  const rows = [
    { id: 'a', days: [{ date: '2026-07-01', count: 2 }, { date: '2026-07-03', count: 0 }] },
    { id: 'b', days: [{ date: '2026-07-01', count: 0 }, { date: '2026-07-03', count: 0 }] },
  ];
  const dates = ['2026-07-01', '2026-07-02', '2026-07-03'];
  const valueFor = (row: (typeof rows)[number], date: string) =>
    row.days.find((day) => day.date === date)?.count ?? 0;

  it('prunes empty rows', () => {
    expect(pruneHeatmapRows(rows, dates, valueFor).map((row) => row.id)).toEqual(['a']);
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
});
