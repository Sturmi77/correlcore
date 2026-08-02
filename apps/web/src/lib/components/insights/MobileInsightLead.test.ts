import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import MobileInsightLead from './MobileInsightLead.svelte';
import type { InsightMaturity, InsightResponse } from '$lib/api/insights';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
  };
});

const insight: InsightResponse = {
  id: 'lead',
  user_id: 'user',
  insight_type: 'spearman',
  tier: 'developing',
  metric: 'mood',
  subject_type: 'metric',
  subject_id: 'energy',
  subject_label: 'Energy',
  effect_size: 0.58,
  confidence: 0.72,
  sample_n: 42,
  statement: 'Mood and energy moved together in recent entries.',
  flags: { causal_claim: false },
  payload: {},
  generated_for_date: '2026-06-20',
  generated_at: '2026-06-20T10:00:00Z',
  created_at: '2026-06-20T10:00:00Z',
  updated_at: '2026-06-20T10:00:00Z',
};

const maturity: InsightMaturity = {
  phase: 'robust',
  phase_index: 4,
  current_entries: 42,
  next_phase_at: null,
  next_phase_label: null,
  entries_until_next: null,
  user_message_key: 'maturity.robust.description',
};

describe('MobileInsightLead', () => {
  it('renders the strongest signal with maturity on the featured card', () => {
    render(MobileInsightLead, { props: { insight, maturity, entryCount: 42 } });

    const lead = screen.getByTestId('mobile-insight-lead');
    const confidence = screen.getByTestId('insight-card-confidence-summary');
    const badge = screen.getByTestId('insight-maturity-badge');

    expect(lead.contains(confidence)).toBe(true);
    expect(lead.contains(badge)).toBe(true);
    expect(screen.queryByTestId('insight-stage-meta')).toBeNull();
    expect(screen.queryByTestId('mobile-insight-maturity')).toBeNull();
  });

  it('shows milestone-only strip when requested', () => {
    render(MobileInsightLead, {
      props: { insight, maturity, entryCount: 42, showMilestone: true },
    });

    expect(screen.getByTestId('mobile-insight-maturity')).toBeTruthy();
    expect(screen.queryByTestId('insight-stage-meta')).toBeNull();
  });

  it('does not repeat the correlation disclaimer beside the lead (#632)', () => {
    render(MobileInsightLead, { props: { insight } });

    expect(screen.queryByTestId('mobile-insight-correlation-note')).toBeNull();
  });

  it('links the featured insight back to trends', () => {
    render(MobileInsightLead, { props: { insight } });
    expect(screen.getByTestId('analysis-cross-link-trends').getAttribute('href')).toBe('/trends');
  });

  it('forwards exploreEvents from the lead card when enabled', async () => {
    const handler = vi.fn();
    const tagInsight = { ...insight, id: 'tag-lead', subject_type: 'tag', subject_id: 'focus' };
    render(MobileInsightLead, {
      props: {
        insight: tagInsight,
        maturity,
        entryCount: 42,
        enableExploreEvents: true,
      },
      events: { exploreEvents: handler },
    });

    await fireEvent.click(screen.getByTestId('insight-card-explore-events'));

    expect(handler).toHaveBeenCalledOnce();
    expect(handler.mock.calls[0]?.[0].detail).toEqual({ id: 'tag-lead' });
  });
});
