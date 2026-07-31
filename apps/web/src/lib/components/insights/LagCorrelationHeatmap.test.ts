import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import LagCorrelationHeatmap from './LagCorrelationHeatmap.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key) };
});

const lagInsight = (id: string, lagDays: number): InsightResponse => ({
  id,
  user_id: 'u1',
  insight_type: 'symptom_cluster',
  tier: 'developing',
  metric: 'mood',
  subject_type: 'metric',
  subject_id: null,
  subject_label: 'Mood',
  effect_size: 0.3,
  confidence: 0.5,
  sample_n: 90,
  statement: null,
  flags: {},
  payload: {
    method: 'lag',
    lag_days: lagDays,
    feature: { kind: 'tag', name: `Feature ${id}` },
    target: { kind: 'metric', name: 'Mood' },
    lag_profile: [
      { lag: 1, r: 0.1 },
      { lag: lagDays, r: 0.42 },
    ],
  },
  generated_for_date: '2026-07-01',
  generated_at: '2026-07-01T00:00:00Z',
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
});

describe('LagCorrelationHeatmap (#488 Phase 2)', () => {
  it('renders a pair × lag grid when at least two lag pairs have a profile', () => {
    const { container } = render(LagCorrelationHeatmap, {
      props: { insights: [lagInsight('a', 2), lagInsight('b', 3)] },
    });

    expect(screen.getByTestId('lag-correlation-heatmap')).toBeTruthy();
    // 2 rows × 7 lag columns.
    expect(container.querySelectorAll('.lag-heatmap__cell')).toHaveLength(14);
    expect(container.querySelectorAll('.lag-heatmap__col-head')).toHaveLength(7);
    // One highlighted (chosen-lag) cell per row.
    expect(container.querySelectorAll('.lag-heatmap__cell--active')).toHaveLength(2);
  });

  it('self-hides below two usable lag pairs', () => {
    render(LagCorrelationHeatmap, { props: { insights: [lagInsight('a', 2)] } });
    expect(screen.queryByTestId('lag-correlation-heatmap')).toBeNull();
  });

  it('translates core-metric identifiers in row labels (#586)', () => {
    const withMetricTarget = (id: string): InsightResponse => ({
      ...lagInsight(id, 2),
      payload: {
        method: 'lag',
        lag_days: 2,
        feature: { kind: 'tag', key: `tag:sport-${id}`, name: `Sport ${id}` },
        // Backend fills target.name from the raw storage key for core metrics.
        target: { kind: 'metric', key: 'mood_score', name: 'mood_score' },
        lag_profile: [
          { lag: 1, r: 0.1 },
          { lag: 2, r: 0.42 },
        ],
      },
    });

    const { container } = render(LagCorrelationHeatmap, {
      props: { insights: [withMetricTarget('a'), withMetricTarget('b')] },
    });

    const label = container.querySelector('.lag-heatmap__row-label')?.textContent ?? '';
    // i18n mock returns the key; the point is it resolved to the token, not the raw name.
    expect(label).toContain('trends.metric.mood');
    expect(label).not.toContain('mood_score');
  });
});
