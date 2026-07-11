/**
 * InsightCard.test.ts
 *
 * Covers all acceptance criteria from issue #163.
 * Uses @testing-library/svelte + vitest.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import InsightCard from './InsightCard.svelte';
import type { InsightMaturity, InsightResponse } from '$lib/api/insights';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string, options?: { values?: Record<string, unknown> }) => {
      if (key === 'home.confidence_scale.entry_count')
        return `Based on ${options?.values?.n} entries`;
      if (key === 'insights.card.sample_meta')
        return `Based on ${options?.values?.n} entries · ${options?.values?.days} days`;
      if (key === 'trends.metric.mood') return 'Mood';
      if (key === 'trends.metric.energy') return 'Energy';
      if (key === 'trends.metric.stress') return 'Stress';
      return key;
    }),
  };
});

// Minimal fixture that satisfies InsightResponse
const INSIGHT: InsightResponse = {
  id: 'test-001',
  user_id: 'u1',
  insight_type: 'spearman',
  tier: 'developing',
  metric: 'mood',
  subject_type: 'tag',
  subject_id: 'sport',
  subject_label: 'sport',
  confidence: 0.72,
  effect_size: 0.38,
  sample_n: 42,
  statement: 'On days you exercised, your mood tended to be higher.',
  flags: {},
  payload: {
    r_value: 0.612,
    rho_value: 0.598,
    p_value: 0.031,
    time_window_days: 60,
    tag_a: 'sport',
    tag_b: 'mood',
  },
  generated_for_date: '2026-05-10',
  generated_at: '2026-05-10T10:00:00Z',
  created_at: '2026-05-10T10:00:00Z',
  updated_at: '2026-05-12T08:00:00Z',
};

const NEGATIVE_INSIGHT: InsightResponse = {
  ...INSIGHT,
  id: 'test-002',
  effect_size: -0.42,
  statement: 'Higher stress correlates with lower mood in your data.',
  subject_id: 'stress',
  subject_label: 'stress',
  payload: { ...INSIGHT.payload, r_value: -0.551, tag_a: 'stress' },
};

const MATURITY: InsightMaturity = {
  phase: 'provisional',
  phase_index: 3,
  current_entries: 21,
  next_phase_at: 30,
  next_phase_label: 'Robust Insights',
  entries_until_next: 9,
  user_message_key: 'maturity.provisional.description',
};

describe('InsightCard', () => {
  // ── Collapsed (Level 1) ──────────────────────────────────────────
  it('renders statement in collapsed state', () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    expect(screen.getByTestId('insight-card-statement').textContent).toContain(
      'On days you exercised'
    );
  });

  it('renders positive direction indicator (↗) for positive effect size', () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    const dir = screen.getByTestId('insight-card-direction');
    expect(dir.textContent?.trim()).toBe('↗');
  });

  it('renders negative direction indicator (↘) for negative effect size', () => {
    render(InsightCard, { props: { insight: NEGATIVE_INSIGHT } });
    const dir = screen.getByTestId('insight-card-direction');
    expect(dir.textContent?.trim()).toBe('↘');
  });

  it('renders title as "metric -> subject" format', () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    expect(screen.getByTestId('insight-card-title').textContent).toContain('mood → sport');
  });

  it('interpolates both entry count and time window in metadata', () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    expect(screen.getByTestId('insight-card-meta').textContent).toContain(
      'Based on 42 entries · 60 days'
    );
  });

  it('marks insights for inactive tags without hiding them', () => {
    render(InsightCard, { props: { insight: INSIGHT, inactiveTagIds: ['sport'] } });

    expect(screen.getByTestId('insight-card-title').textContent).toContain(
      'insights.card.inactive_tag_badge'
    );
    expect(screen.getByTestId('insight-card-meta').textContent).toContain(
      'insights.card.inactive_tag_hint'
    );
  });

  it('does NOT show raw percentage in collapsed state', () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    expect(screen.queryByTestId('insight-confidence-score-percent')).toBeNull();
  });

  it('shows semantic confidence without a raw percentage for a featured mobile card', () => {
    render(InsightCard, {
      props: { insight: INSIGHT, featured: true, showConfidenceSummary: true },
    });

    expect(screen.getByTestId('insight-card').getAttribute('data-featured')).toBe('true');
    expect(screen.getByTestId('insight-card-confidence-summary')).toBeTruthy();
    expect(screen.getByTestId('insight-confidence-label')).toBeTruthy();
    expect(screen.queryByTestId('insight-confidence-score-percent')).toBeNull();
  });

  it('replaces the confidence summary with detailed confidence after expansion', async () => {
    render(InsightCard, {
      props: { insight: INSIGHT, featured: true, showConfidenceSummary: true },
    });

    await fireEvent.click(screen.getByTestId('insight-card-toggle'));

    expect(screen.queryByTestId('insight-card-confidence-summary')).toBeNull();
    expect(screen.getByTestId('insight-confidence-score-percent')).toBeTruthy();
  });

  it('hides the maturity badge when page chrome owns phase display', () => {
    render(InsightCard, {
      props: { insight: INSIGHT, maturity: MATURITY, showMaturityBadge: false },
    });
    expect(screen.queryByTestId('insight-maturity-badge')).toBeNull();
  });

  it('renders a maturity badge when maturity is provided', () => {
    render(InsightCard, { props: { insight: INSIGHT, maturity: MATURITY } });
    const badge = screen.getByTestId('insight-maturity-badge');

    expect(badge.getAttribute('data-phase')).toBe('provisional');
    expect(badge.textContent).toContain('maturity.badge.provisional');
  });

  it('does not show explore-events action unless the parent opts in', () => {
    render(InsightCard, { props: { insight: INSIGHT, maturity: MATURITY } });

    expect(screen.queryByTestId('insight-card-explore-events')).toBeNull();
  });

  it('dispatches exploreEvents when the wired affordance is enabled', async () => {
    const handler = vi.fn();
    render(InsightCard, {
      props: {
        insight: INSIGHT,
        maturity: MATURITY,
        enableExploreEvents: true,
      },
      events: { exploreEvents: handler },
    });

    await fireEvent.click(screen.getByTestId('insight-card-explore-events'));

    expect(handler).toHaveBeenCalledOnce();
    expect(handler.mock.calls[0]?.[0].detail).toEqual({ id: INSIGHT.id });
  });

  it('renders disclaimer link', () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    const link = screen.getByTestId('insight-card-disclaimer');
    expect(link).toBeTruthy();
    expect(link.tagName.toLowerCase()).toBe('a');
  });

  it('expand toggle has correct ARIA attributes in collapsed state', () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    const toggle = screen.getByTestId('insight-card-toggle');
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
  });

  // ── Expanding to Level 2 ─────────────────────────────────────────
  it('clicking expand toggle shows the level 2 detail section', async () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    const toggle = screen.getByTestId('insight-card-toggle');
    await fireEvent.click(toggle);
    expect(screen.getByTestId('insight-card-level2')).toBeTruthy();
    expect(screen.getByTestId('insight-card-tech-meta')).toBeTruthy();
  });

  it('aria-expanded is true after expanding', async () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    const toggle = screen.getByTestId('insight-card-toggle');
    await fireEvent.click(toggle);
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
  });

  it('level 2 shows effect size when present', async () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    await fireEvent.click(screen.getByTestId('insight-card-toggle'));
    expect(screen.getByTestId('insight-card-effect-size').textContent).toContain('0.380');
  });

  it('level 2 shows raw confidence float', async () => {
    render(InsightCard, { props: { insight: INSIGHT } });
    await fireEvent.click(screen.getByTestId('insight-card-toggle'));
    expect(screen.getByTestId('insight-card-confidence-raw').textContent).toContain('72');
  });

  // ── States ───────────────────────────────────────────────────────
  it('renders skeleton when loading=true', () => {
    render(InsightCard, { props: { loading: true } });
    expect(screen.getByTestId('insight-card-skeleton')).toBeTruthy();
  });

  it('renders error state with retry button when error is set', () => {
    render(InsightCard, { props: { error: 'Network failure' } });
    expect(screen.getByTestId('insight-card-error')).toBeTruthy();
    expect(screen.getByTestId('insight-card-retry')).toBeTruthy();
  });

  it('dispatches retry event when retry button is clicked', async () => {
    const handler = vi.fn();
    render(InsightCard, { props: { error: 'err' }, events: { retry: handler } });
    await fireEvent.click(screen.getByTestId('insight-card-retry'));
    expect(handler).toHaveBeenCalledOnce();
  });

  it('renders confounded variant with explanatory subtitle', () => {
    render(InsightCard, {
      props: {
        insight: {
          ...INSIGHT,
          payload: { ...INSIGHT.payload, confounder: 'weekday' },
        },
      },
    });

    expect(screen.getByTestId('insight-card-confounder')).toBeTruthy();
    expect(screen.getByTestId('insight-card').className).toContain('insight-card--confounded');
  });

  it('renders work context pattern cards with context badge and title label', () => {
    render(InsightCard, {
      props: {
        insight: {
          ...INSIGHT,
          insight_type: 'work_context_pattern',
          metric: 'mood_score',
          subject_label: null,
          payload: { work_context: 'office', work_context_label: 'Office' },
        },
      },
    });

    expect(screen.getByTestId('insight-card-title').textContent).toContain('Mood -> Office');
    expect(screen.getByTestId('insight-card-context-badge')).toBeTruthy();
  });

  it('uses work-context confounder copy when marked by flags', () => {
    render(InsightCard, {
      props: {
        insight: {
          ...INSIGHT,
          flags: { work_context_confounded: true },
        },
      },
    });

    expect(screen.getByTestId('insight-card-confounder').textContent).toContain(
      'insights.work_context_confounded_note'
    );
  });
});
