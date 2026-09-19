import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import type { EventMarker } from '$lib/components/trends/EventMarkerLayer.svelte';
import {
  formatChangepointStatement,
  insightsToChangepointMarkers,
  insightsToChangepointSegments,
  parseChangepointPayload,
  pinIsoDateToAxisKeys,
  remapEventMarkersToDisplayAxis,
  scoreToPlotY,
} from './changepointMarkers';
import type { AxisBucket } from './compareAxisZoom';

function insight(overrides: Partial<InsightResponse> = {}): InsightResponse {
  return {
    id: 'cp-1',
    user_id: 'u1',
    insight_type: 'changepoint',
    tier: 'robust',
    metric: 'mood_changepoint',
    subject_type: 'changepoint',
    subject_id: null,
    subject_label: '2026-03-07',
    effect_size: 1.2,
    confidence: 0.8,
    sample_n: 80,
    statement: 'Your mood average shifted to higher levels around 2026-03-07 (from 2026-03-09).',
    flags: {},
    payload: {
      changepoint_index: 3,
      changepoint_date: '2026-03-07',
      shift_date: '2026-03-09',
      before_avg: 2.1,
      after_avg: 4.0,
      changepoints: [3],
      changepoint_dates: [{ index: 3, changepoint_date: '2026-03-07', shift_date: '2026-03-09' }],
    },
    generated_for_date: '2026-04-01',
    generated_at: '2026-04-01T00:00:00Z',
    created_at: '2026-04-01T00:00:00Z',
    updated_at: '2026-04-01T00:00:00Z',
    ...overrides,
  };
}

describe('parseChangepointPayload', () => {
  it('reads ISO dates and averages', () => {
    expect(parseChangepointPayload(insight().payload)).toEqual({
      changepointDate: '2026-03-07',
      shiftDate: '2026-03-09',
      beforeAvg: 2.1,
      afterAvg: 4.0,
      dates: [{ index: 3, changepoint_date: '2026-03-07', shift_date: '2026-03-09' }],
    });
  });

  it('returns null when dates are missing', () => {
    expect(parseChangepointPayload({ before_avg: 2, after_avg: 4 })).toBeNull();
  });
});

describe('insightsToChangepointMarkers', () => {
  it('emits phase_transition markers on shift_date', () => {
    const markers = insightsToChangepointMarkers([insight()], {
      label: 'Niveauwechsel',
      descriptionFor: (before, after) => `${before}→${after}`,
    });
    expect(markers).toEqual([
      {
        date: '2026-03-09',
        kind: 'phase_transition',
        label: 'Niveauwechsel',
        description: '2.1→4',
      },
    ]);
  });

  it('ignores non-changepoint insights', () => {
    expect(
      insightsToChangepointMarkers([{ ...insight(), insight_type: 'spearman' }], {
        label: 'x',
        descriptionFor: () => 'y',
      })
    ).toEqual([]);
  });
});

describe('insightsToChangepointSegments', () => {
  it('returns primary segment guides', () => {
    expect(insightsToChangepointSegments([insight()])).toEqual([
      {
        changepointDate: '2026-03-07',
        shiftDate: '2026-03-09',
        beforeAvg: 2.1,
        afterAvg: 4.0,
      },
    ]);
  });
});

describe('formatChangepointStatement', () => {
  it('builds localized copy from payload', () => {
    const t = (key: string, options?: { values?: Record<string, string | number> }) => {
      if (key === 'insights.card.changepoint_direction_higher') return 'higher';
      if (key === 'insights.card.changepoint_statement') {
        const v = options?.values ?? {};
        return `shift ${v.date} ${v.before}→${v.after} (${v.direction})`;
      }
      return key;
    };
    expect(formatChangepointStatement(insight(), t)).toBe('shift 2026-03-09 2.1→4.0 (higher)');
  });
});

describe('pinIsoDateToAxisKeys', () => {
  const axis = ['2026-03-01', '2026-03-02', '2026-03-03'];

  it('keeps in-range dates', () => {
    expect(pinIsoDateToAxisKeys('2026-03-02', axis)).toBe('2026-03-02');
  });

  it('pins dates before the window to the first key', () => {
    expect(pinIsoDateToAxisKeys('2026-02-01', axis)).toBe('2026-03-01');
  });

  it('pins dates after the window to the last key', () => {
    expect(pinIsoDateToAxisKeys('2026-04-01', axis)).toBe('2026-03-03');
  });
});

describe('remapEventMarkersToDisplayAxis', () => {
  it('clamps out-of-window markers to edge keys', () => {
    const markers: EventMarker[] = [{ date: '2025-01-01', kind: 'phase_transition', label: 'CP' }];
    expect(remapEventMarkersToDisplayAxis(markers, ['2026-01-01', '2026-01-02'])).toEqual([
      { date: '2026-01-01', kind: 'phase_transition', label: 'CP', endDate: undefined },
    ]);
  });

  it('remaps onto bucket starts under zoom', () => {
    const buckets: AxisBucket[] = [
      {
        id: 'a',
        start: '2026-03-01',
        end: '2026-03-02',
        dayCount: 2,
        presentDays: 2,
        partial: false,
        dates: ['2026-03-01', '2026-03-02'],
      },
      {
        id: 'b',
        start: '2026-03-03',
        end: '2026-03-04',
        dayCount: 2,
        presentDays: 2,
        partial: false,
        dates: ['2026-03-03', '2026-03-04'],
      },
    ];
    const markers: EventMarker[] = [{ date: '2026-03-04', kind: 'phase_transition', label: 'CP' }];
    expect(remapEventMarkersToDisplayAxis(markers, [], buckets)).toEqual([
      { date: '2026-03-03', kind: 'phase_transition', label: 'CP', endDate: undefined },
    ]);
  });

  it('pins out-of-window dates to the edge bucket under zoom', () => {
    const buckets: AxisBucket[] = [
      {
        id: 'a',
        start: '2026-03-01',
        end: '2026-03-02',
        dayCount: 2,
        presentDays: 2,
        partial: false,
        dates: ['2026-03-01', '2026-03-02'],
      },
      {
        id: 'b',
        start: '2026-03-03',
        end: '2026-03-04',
        dayCount: 2,
        presentDays: 2,
        partial: false,
        dates: ['2026-03-03', '2026-03-04'],
      },
    ];
    const markers: EventMarker[] = [{ date: '2026-06-01', kind: 'phase_transition', label: 'CP' }];
    expect(remapEventMarkersToDisplayAxis(markers, [], buckets)[0]?.date).toBe('2026-03-03');
  });
});

describe('scoreToPlotY', () => {
  it('maps 1–5 onto plot height', () => {
    expect(scoreToPlotY(1, 100)).toBe(100);
    expect(scoreToPlotY(5, 100)).toBe(0);
    expect(scoreToPlotY(3, 100)).toBe(50);
  });
});
