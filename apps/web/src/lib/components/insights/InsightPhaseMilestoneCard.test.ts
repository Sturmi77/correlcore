import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import InsightPhaseMilestoneCard from './InsightPhaseMilestoneCard.svelte';
import type { InsightMaturity } from '$lib/api/insights';

vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (run: (formatter: (key: string) => string) => void) => {
      run((key: string) => key);
      return () => undefined;
    },
  },
}));

const maturity: InsightMaturity = {
  phase: 'early_patterns',
  phase_index: 2,
  current_entries: 7,
  next_phase_at: 14,
  next_phase_label: 'Provisional Insights',
  entries_until_next: 7,
  user_message_key: 'maturity.early_patterns.description',
};

describe('InsightPhaseMilestoneCard', () => {
  it('renders a non-toast milestone card for non-collecting phases', () => {
    render(InsightPhaseMilestoneCard, { props: { maturity } });

    const card = screen.getByTestId('insight-phase-milestone-card');
    expect(card.getAttribute('data-phase')).toBe('early_patterns');
    expect(screen.getByText('maturity.milestone_card.early_patterns.title')).toBeTruthy();
  });

  it('dispatches explicit dismiss with the milestone key', async () => {
    const handler = vi.fn();
    render(InsightPhaseMilestoneCard, {
      props: { maturity },
      events: { dismiss: handler },
    });

    await fireEvent.click(screen.getByText('maturity.milestone_card.dismiss'));

    expect(handler).toHaveBeenCalledOnce();
    expect(handler.mock.calls[0][0].detail.key).toBe('maturity_phase_early_patterns');
  });

  it('does not render for collecting', () => {
    render(InsightPhaseMilestoneCard, {
      props: { maturity: { ...maturity, phase: 'collecting', phase_index: 1 } },
    });

    expect(screen.queryByTestId('insight-phase-milestone-card')).toBeNull();
  });
});
