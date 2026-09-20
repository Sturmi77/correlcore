import { describe, expect, it } from 'vitest';
import { confidenceLabelKey } from './confidenceLabel';

describe('confidenceLabelKey', () => {
  it('maps boundary scores to the documented bands', () => {
    expect(confidenceLabelKey(0)).toBe('early_signal');
    expect(confidenceLabelKey(0.19)).toBe('early_signal');
    expect(confidenceLabelKey(0.2)).toBe('emerging_pattern');
    expect(confidenceLabelKey(0.39)).toBe('emerging_pattern');
    expect(confidenceLabelKey(0.4)).toBe('moderate_finding');
    expect(confidenceLabelKey(0.59)).toBe('moderate_finding');
    expect(confidenceLabelKey(0.6)).toBe('strong_finding');
    expect(confidenceLabelKey(0.79)).toBe('strong_finding');
    expect(confidenceLabelKey(0.8)).toBe('very_strong_finding');
    expect(confidenceLabelKey(1)).toBe('very_strong_finding');
  });

  it('clamps out-of-range inputs', () => {
    expect(confidenceLabelKey(-1)).toBe('early_signal');
    expect(confidenceLabelKey(2)).toBe('very_strong_finding');
  });
});
