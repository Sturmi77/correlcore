import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import InsightMaturityBadge from './InsightMaturityBadge.svelte';
import type { InsightMaturity } from '$lib/api/insights';

vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (run: (formatter: (key: string) => string) => void) => {
      run((key: string) => key);
      return () => undefined;
    },
  },
}));

function maturity(overrides: Partial<InsightMaturity> = {}): InsightMaturity {
  return {
    phase: 'early_patterns',
    phase_index: 2,
    current_entries: 9,
    next_phase_at: 14,
    next_phase_label: 'Provisional Insights',
    entries_until_next: 5,
    user_message_key: 'maturity.early_patterns.description',
    ...overrides,
  };
}

describe('InsightMaturityBadge', () => {
  it('renders phase-specific copy from maturity', () => {
    render(InsightMaturityBadge, { props: { maturity: maturity(), entryCount: 9 } });

    const badge = screen.getByTestId('insight-maturity-badge');
    expect(badge.getAttribute('data-phase')).toBe('early_patterns');
    expect(badge.textContent).toContain('maturity.badge.early_patterns');
  });

  it('marks early and provisional phases as uncertain', () => {
    render(InsightMaturityBadge, {
      props: { maturity: maturity({ phase: 'provisional', phase_index: 3 }), entryCount: 21 },
    });

    expect(screen.getByTestId('insight-maturity-badge').textContent).toContain('!');
  });

  it('does not render raw confidence values', () => {
    render(InsightMaturityBadge, {
      props: { maturity: maturity({ phase: 'robust', phase_index: 4 }), entryCount: 42 },
    });

    expect(screen.getByTestId('insight-maturity-badge').textContent).not.toContain('72');
    expect(screen.getByTestId('insight-maturity-badge').textContent).not.toContain('%');
  });
});
