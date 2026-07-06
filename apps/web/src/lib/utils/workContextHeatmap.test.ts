import { describe, expect, it } from 'vitest';
import type { EntryResponse } from '$lib/api/entries';
import { buildWorkContextHeatmap } from './workContextHeatmap';

function entry(date: string, work_context: EntryResponse['work_context']): EntryResponse {
  return {
    id: `${date}-${work_context}`,
    user_id: 'u1',
    entry_date: date,
    slot: 'day',
    mood_score: 3,
    energy: 3,
    stress: 3,
    cycle_day: null,
    source: 'direct',
    work_context,
    note: null,
    created_at: `${date}T08:00:00Z`,
    updated_at: `${date}T08:00:00Z`,
  };
}

describe('workContextHeatmap', () => {
  it('aggregates work context presence per day within the selected window', () => {
    const heatmap = buildWorkContextHeatmap(
      [
        entry('2026-07-01', 'office'),
        entry('2026-07-01', 'office'),
        entry('2026-07-02', 'homeoffice'),
        entry('2026-07-03', 'weekend'),
        entry('2026-06-30', 'travel'),
      ],
      { start_date: '2026-07-01', end_date: '2026-07-03' }
    );

    expect(heatmap.start_date).toBe('2026-07-01');
    expect(heatmap.end_date).toBe('2026-07-03');
    expect(heatmap.contexts).toEqual([
      { context: 'homeoffice', days: [{ date: '2026-07-02', count: 1 }] },
      { context: 'office', days: [{ date: '2026-07-01', count: 1 }] },
      { context: 'weekend', days: [{ date: '2026-07-03', count: 1 }] },
    ]);
  });
});
