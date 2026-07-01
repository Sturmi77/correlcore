import { describe, expect, it } from 'vitest';
import { NEUTRAL_SCALE_DEFAULT, scaleDefaultsFromPrevious } from './entrySmartDefaults';

describe('entrySmartDefaults', () => {
  it('returns previous scale values when available', () => {
    expect(
      scaleDefaultsFromPrevious({
        entry_date: '2026-06-01',
        slot: 'day',
        mood_score: 4,
        energy: 2,
        stress: 5,
      })
    ).toEqual({ mood_score: 4, energy: 2, stress: 5 });
  });

  it('falls back to neutral defaults when no previous entry exists', () => {
    expect(scaleDefaultsFromPrevious(null)).toBeNull();
    expect(NEUTRAL_SCALE_DEFAULT).toBe(3);
  });
});
