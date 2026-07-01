import { describe, expect, it } from 'vitest';
import type { InsightMaturity } from '$lib/api/insights';
import { maturityProgressMessage, maturityProgressPercent } from './insightMaturityProgress';

const collecting: InsightMaturity = {
  phase: 'collecting',
  phase_index: 1,
  current_entries: 4,
  next_phase_at: 7,
  next_phase_label: 'early_patterns',
  entries_until_next: 3,
  user_message_key: 'maturity.collecting.description',
};

describe('insightMaturityProgress', () => {
  it('formats compact entries-until-next copy', () => {
    const message = maturityProgressMessage(collecting, (key, options) => {
      expect(key).toBe('maturity.journey.compact_entries_until_next');
      return `${options?.values?.remaining} left`;
    });
    expect(message).toBe('3 left');
  });

  it('uses robust meta when phase is robust', () => {
    const message = maturityProgressMessage(
      { ...collecting, phase: 'robust', next_phase_at: null, entries_until_next: null },
      (key) => key
    );
    expect(message).toBe('maturity.journey.robust_meta');
  });

  it('computes progress percent within the current phase span', () => {
    expect(maturityProgressPercent(collecting)).toBe(57);
    expect(maturityProgressPercent({ ...collecting, phase: 'robust', next_phase_at: null })).toBe(100);
  });
});
