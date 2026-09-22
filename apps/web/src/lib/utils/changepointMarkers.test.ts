import { describe, expect, it } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import {
  changepointInsightsToMarkers,
  formatChangepointStatement,
  isChangepointInsight,
} from './changepointMarkers';

function t(key: string, opts?: { values?: Record<string, unknown> }): string {
  const values = opts?.values ?? {};
  return `${key}:${JSON.stringify(values)}`;
}

function changepoint(overrides: Partial<InsightResponse> = {}): InsightResponse {
  return {
    id: 'cp1',
    user_id: 'u1',
    insight_type: 'changepoint',
    tier: 'robust',
    metric: 'stress_changepoint',
    subject_type: 'changepoint',
    subject_id: null,
    subject_label: '2026-03-10',
    effect_size: 1.2,
    confidence: 0.5,
    sample_n: 80,
    statement: 'raw english',
    flags: {},
    payload: {
      series: 'stress',
      changepoint_date: '2026-03-10',
      shift_date: '2026-03-11',
      before_avg: 2.1,
      after_avg: 4.0,
    },
    generated_for_date: '2026-05-01',
    generated_at: '2026-05-01T00:00:00Z',
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
    ...overrides,
  };
}

describe('changepointMarkers', () => {
  it('detects changepoint insights', () => {
    expect(isChangepointInsight(changepoint())).toBe(true);
  });

  it('formats a localized statement from payload', () => {
    const text = formatChangepointStatement(changepoint(), t);
    expect(text).toContain('insights.changepoint.statement');
    expect(text).toContain('2026-03-10');
  });

  it('maps insights to phase_transition markers and clamps to axis edges', () => {
    const markers = changepointInsightsToMarkers([changepoint()], t, {
      axisStart: '2026-04-01',
      axisEnd: '2026-04-30',
    });
    expect(markers).toHaveLength(1);
    expect(markers[0].kind).toBe('phase_transition');
    expect(markers[0].date).toBe('2026-04-01');
  });
});

describe('stress is read on the scale it is plotted on (#955)', () => {
  const stressCp = (before: number, after: number) =>
    changepoint({
      payload: { series: 'stress', before_avg: before, after_avg: after, shift_date: '2026-03-11' },
    });

  it('names the actual raw-stress direction and exposes the plotted values', () => {
    const out = formatChangepointStatement(stressCp(2.1, 4.0), t) ?? '';
    expect(out).toContain('statement_stress');
    expect(out).toContain('direction_higher');
    expect(out).toContain('"displayBefore":"3.9"');
    expect(out).toContain('"displayAfter":"2.0"');
  });

  it('keeps raw values separate and plots inverted stress in markers', () => {
    const out = formatChangepointStatement(stressCp(2.1, 4.0), t) ?? '';
    expect(out).toContain('"before":"2.1"');
    expect(out).toContain('"after":"4.0"');
    const markers = changepointInsightsToMarkers([stressCp(2.1, 4.0)], t);
    expect(markers[0].description).toContain('"before":"3.9"');
    expect(markers[0].description).toContain('"after":"2.0"');
  });

  it('handles falling and unchanged stress without inventing a direction', () => {
    expect(formatChangepointStatement(stressCp(5, 2), t)).toContain('direction_lower');
    expect(formatChangepointStatement(stressCp(3, 3), t)).toContain('direction_unchanged');
    expect(formatChangepointStatement(stressCp(3, Number.NaN), t)).toBeNull();
  });

  it('leaves a non-inverted metric alone', () => {
    const mood = changepoint({
      metric: 'mood_changepoint',
      payload: { series: 'mood_score', before_avg: 2.0, after_avg: 4.0 },
    });
    const out = formatChangepointStatement(mood, t) ?? '';
    expect(out).toContain('direction_higher');
    expect(out).toContain('"after":"4.0"');
  });
});
