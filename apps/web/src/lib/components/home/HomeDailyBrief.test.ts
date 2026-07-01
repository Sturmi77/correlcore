import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import HomeDailyBrief from './HomeDailyBrief.svelte';
import type { InsightMaturity } from '$lib/api/insights';

vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (
      run: (
        formatter: (key: string, options?: { values?: Record<string, unknown> }) => string
      ) => void
    ) => {
      run((key: string, options?: { values?: Record<string, unknown> }) => {
        if (key === 'maturity.journey.compact_entries_until_next') {
          return `${options?.values?.remaining} more until next phase`;
        }
        if (key.startsWith('maturity.')) return key;
        return key;
      });
      return () => undefined;
    },
  },
}));

const collectingMaturity: InsightMaturity = {
  phase: 'collecting',
  phase_index: 1,
  current_entries: 4,
  next_phase_at: 7,
  next_phase_label: 'early_patterns',
  entries_until_next: 3,
  user_message_key: 'maturity.collecting.description',
};

describe('HomeDailyBrief', () => {
  it('shows inline entries-until-milestone progress when maturity is present', () => {
    render(HomeDailyBrief, {
      props: {
        maturity: collectingMaturity,
        entries: [],
      },
    });

    expect(screen.getByTestId('home-brief-milestone-progress').textContent).toContain(
      '3 more until next phase'
    );
    expect(screen.getByRole('meter')).toBeTruthy();
  });

  it('enriches weekly bridge links with insight and trend previews', () => {
    render(HomeDailyBrief, {
      props: {
        maturity: collectingMaturity,
        entries: [{ id: '1' } as never, { id: '2' } as never, { id: '3' } as never],
        latestInsight: {
          id: 'i1',
          subject_label: 'Energy',
          metric: 'energy',
        } as never,
        tagHeatmap: {
          tags: [
            {
              name: 'Walk',
              days: [{ date: '2026-06-01', count: 2 }],
            },
          ],
        } as never,
      },
    });

    expect(screen.getByTestId('home-bridge-insights').textContent).toContain('Energy');
    expect(screen.getByTestId('home-bridge-trends').textContent).toContain('Walk');
  });
});
