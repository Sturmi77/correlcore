import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import InsightJourneyBanner from './InsightJourneyBanner.svelte';
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
  current_entries: 9,
  next_phase_at: 14,
  next_phase_label: 'Provisional Insights',
  entries_until_next: 5,
  user_message_key: 'maturity.early_patterns.description',
};

describe('InsightJourneyBanner', () => {
  it('renders the backend-owned maturity phase', () => {
    render(InsightJourneyBanner, { props: { maturity } });

    const banner = screen.getByTestId('insight-journey-banner');
    expect(banner.getAttribute('data-phase')).toBe('early_patterns');
    expect(screen.getByText('maturity.early_patterns.label')).toBeTruthy();
    expect(screen.getByTestId('insight-journey-meta')).toBeTruthy();
  });

  it('opens the explainer bottom sheet from the help action', async () => {
    render(InsightJourneyBanner, { props: { maturity } });

    await fireEvent.click(screen.getByText('maturity.journey.help_cta'));

    expect(screen.getByTestId('insight-journey-explainer')).toBeTruthy();
  });

  it('supports the collapsed Home variant', async () => {
    render(InsightJourneyBanner, {
      props: { maturity, collapsible: true, initialCollapsed: true },
    });

    expect(screen.queryByTestId('insight-journey-meta')).toBeNull();
    await fireEvent.click(screen.getByText('maturity.journey.expand'));
    expect(screen.getByTestId('insight-journey-meta')).toBeTruthy();
  });
});
