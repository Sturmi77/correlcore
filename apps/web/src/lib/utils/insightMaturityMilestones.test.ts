import { describe, expect, it } from 'vitest';
import type { InsightMaturity } from '$lib/api/insights';
import { maturityMilestoneKey, shouldShowMaturityMilestone } from './insightMaturityMilestones';

const maturity: InsightMaturity = {
  phase: 'early_patterns',
  phase_index: 2,
  current_entries: 7,
  next_phase_at: 14,
  next_phase_label: 'Provisional Insights',
  entries_until_next: 7,
  user_message_key: 'maturity.early_patterns.description',
};

describe('insight maturity milestones', () => {
  it('does not create a milestone key for collecting', () => {
    expect(maturityMilestoneKey('collecting')).toBeNull();
  });

  it('creates stable keys for phase transitions', () => {
    expect(maturityMilestoneKey('early_patterns')).toBe('maturity_phase_early_patterns');
    expect(maturityMilestoneKey('provisional')).toBe('maturity_phase_provisional');
    expect(maturityMilestoneKey('robust')).toBe('maturity_phase_robust');
  });

  it('shows unseen non-collecting milestones once', () => {
    expect(shouldShowMaturityMilestone(maturity, [])).toBe(true);
    expect(shouldShowMaturityMilestone(maturity, ['maturity_phase_early_patterns'])).toBe(false);
  });
});
