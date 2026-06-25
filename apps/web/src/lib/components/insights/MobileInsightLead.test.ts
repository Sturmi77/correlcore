import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
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
  it('renders the strongest signal with visible confidence before maturity', () => {
    render(MobileInsightLead, { props: { insight, maturity, entryCount: 42 } });

    const lead = screen.getByTestId('mobile-insight-lead');
    const confidence = screen.getByTestId('insight-card-confidence-summary');
    const maturityContext = screen.getByTestId('mobile-insight-maturity');

    expect(lead.contains(confidence)).toBe(true);
    expect(lead.contains(maturityContext)).toBe(true);
    expect(screen.queryByTestId('insight-maturity-badge')).toBeNull();
    expect(
      confidence.compareDocumentPosition(maturityContext) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });

  it('keeps non-causal guidance visible beside the lead insight', () => {
    render(MobileInsightLead, { props: { insight } });

    const note = screen.getByTestId('mobile-insight-correlation-note');
    expect(note).toBeTruthy();
    expect(within(note).getByRole('link').getAttribute('href')).toBe('/insights/disclaimer');
  });
});
