import { describe, expect, it } from 'vitest';
import { rangeToDays, rangeToHabitWindow } from './trendsRange';

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
});
