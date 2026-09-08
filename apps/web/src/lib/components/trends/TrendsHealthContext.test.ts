/**
 * TrendsHealthContext.test.ts — Health Data Maturity panel (Issue #852).
 *
 * Verifies the panel renders coverage meters, honours per-section gates
 * (progressive disclosure), shows no streak-record numbers, keeps the cycle
 * strip as a separate neutral section, and reuses InsightStageHeader (G1).
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import TrendsHealthContext from './TrendsHealthContext.svelte';
import type { HealthContextResponse } from '$lib/api/stats';
import type { InsightMaturity } from '$lib/api/insights';
import type { EntryResponse } from '$lib/api/entries';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: {
      subscribe: (run: (formatter: (key: string) => string) => void) => {
        run((key: string) => key);
        return () => undefined;
      },
    },
    locale: readable('en'),
  };
});

function makeHealthContext(overrides: Partial<HealthContextResponse> = {}): HealthContextResponse {
  return {
    as_of: '2026-09-07',
    coverage_window_days: 90,
    maturity: {
      phase: 'provisional',
      phase_index: 3,
      current_entries: 24,
      next_phase_at: 30,
      entries_until_next: 6,
    },
    coverage: {
      entry: { days_with_data: 22, window_days: 90, pct: 0.24 },
      sleep: { days_with_data: 3, window_days: 90, pct: 0.03 },
      symptom: { days_with_data: 16, window_days: 90, pct: 0.18 },
    },
    sections: [
      {
        id: 'symptom',
        unlocked: true,
        reason: 'ok',
        entries_until_unlock: null,
        copy_key: 'trends.maturity.symptom.ok',
      },
      {
        id: 'sleep',
        unlocked: false,
        reason: 'insufficient_coverage',
        entries_until_unlock: null,
        copy_key: 'trends.maturity.sleep.insufficient_coverage',
      },
    ],
    health_connect: null,
    ...overrides,
  };
}

const maturity: InsightMaturity = {
  phase: 'provisional',
  phase_index: 3,
  current_entries: 24,
  next_phase_at: 30,
  next_phase_label: 'Robust Insights',
  entries_until_next: 6,
  user_message_key: 'maturity.provisional.description',
};

describe('TrendsHealthContext', () => {
  it('renders one meter per coverage row with its percentage', () => {
    render(TrendsHealthContext, { healthContext: makeHealthContext(), maturity: null });

    const meters = screen.getAllByRole('meter');
    expect(meters).toHaveLength(3);
    const values = meters.map((m) => m.getAttribute('aria-valuenow'));
    // entry 24 %, symptom 18 %, sleep 3 %
    expect(values).toEqual(['24', '18', '3']);
  });

  it('locks a gated section and shows its insufficient copy, no deep link', () => {
    render(TrendsHealthContext, { healthContext: makeHealthContext(), maturity: null });

    // Sleep is gated -> shows the "locked" label and the insufficient copy key.
    expect(screen.getByText('trends.maturity.locked')).toBeTruthy();
    expect(screen.getByText('trends.maturity.sleep.insufficient_coverage')).toBeTruthy();
    // Unlocked symptom section exposes its deep link; the gated sleep one does not.
    expect(screen.getByText('trends.maturity.symptom.deep_link')).toBeTruthy();
    expect(screen.queryByText('trends.maturity.sleep.deep_link')).toBeNull();
  });

  it('shows no gamifying streak-record numbers', () => {
    const { container } = render(TrendsHealthContext, {
      healthContext: makeHealthContext(),
      maturity: null,
    });
    // The removed streak block used trends.consistency.* labels — ensure gone.
    expect(container.textContent).not.toContain('trends.consistency');
    expect(screen.queryByText(/Beste Kontinuit/i)).toBeNull();
  });

  it('renders the cycle strip as a separate neutral-context section', () => {
    const cycleEntries = [
      { entry_date: '2026-09-06', cycle_day: 12 } as EntryResponse,
      { entry_date: '2026-09-07', cycle_day: 13 } as EntryResponse,
    ];
    render(TrendsHealthContext, {
      healthContext: makeHealthContext(),
      maturity: null,
      cycleEntries,
    });
    expect(screen.getByText('trends.maturity.cycle_context')).toBeTruthy();
    expect(screen.getByText('trends.cycle.heading')).toBeTruthy();
  });

  it('reuses InsightStageHeader for the maturity surface (G1)', () => {
    render(TrendsHealthContext, { healthContext: makeHealthContext(), maturity });
    expect(screen.getByTestId('insight-stage-header')).toBeTruthy();
  });

  it('omits the maturity surface when no maturity is provided', () => {
    render(TrendsHealthContext, { healthContext: makeHealthContext(), maturity: null });
    expect(screen.queryByTestId('insight-stage-header')).toBeNull();
  });
});
