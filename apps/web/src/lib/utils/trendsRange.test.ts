import { describe, expect, it } from 'vitest';
import {
  rangeToDays,
  rangeToHabitWindow,
  readSmoothingPreference,
  smoothingWindowDays,
  TREND_SMOOTHING_STORAGE_KEY,
} from './trendsRange';

describe('trendsRange', () => {
  it('maps range ids to day counts', () => {
    expect(rangeToDays('week')).toBe(7);
    expect(rangeToDays('month')).toBe(30);
    expect(rangeToDays('quarter')).toBe(90);
    expect(rangeToDays('year')).toBe(365);
  });

  it('maps global range to habit windows', () => {
    expect(rangeToHabitWindow('week')).toBe(7);
    expect(rangeToHabitWindow('month')).toBe(28);
    expect(rangeToHabitWindow('quarter')).toBe(90);
    expect(rangeToHabitWindow('year')).toBe(90);
  });

  it('uses a short SMA window for week and 7 days otherwise', () => {
    expect(smoothingWindowDays('week')).toBe(3);
    expect(smoothingWindowDays('month')).toBe(7);
    expect(smoothingWindowDays('quarter')).toBe(7);
    expect(smoothingWindowDays('year')).toBe(7);
  });

  it('defaults smoothing on when preference is unset', () => {
    const storage = {
      getItem: () => null,
    };
    expect(readSmoothingPreference(storage)).toBe(true);
    expect(readSmoothingPreference(null)).toBe(true);
  });

  it('honours an explicit Raw preference', () => {
    const storage = {
      getItem: (key: string) => (key === TREND_SMOOTHING_STORAGE_KEY ? 'false' : null),
    };
    expect(readSmoothingPreference(storage)).toBe(false);
  });
});
