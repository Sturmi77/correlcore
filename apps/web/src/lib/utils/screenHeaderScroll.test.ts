import { describe, expect, it } from 'vitest';
import {
  nextScreenHeaderScrolled,
  SCREEN_HEADER_COLLAPSE_Y,
  SCREEN_HEADER_EXPAND_Y,
} from './screenHeaderScroll';

describe('nextScreenHeaderScrolled (#851)', () => {
  it('stays expanded below the collapse threshold', () => {
    expect(nextScreenHeaderScrolled(0, false)).toBe(false);
    expect(nextScreenHeaderScrolled(SCREEN_HEADER_COLLAPSE_Y - 1, false)).toBe(false);
  });

  it('collapses at or above the collapse threshold', () => {
    expect(nextScreenHeaderScrolled(SCREEN_HEADER_COLLAPSE_Y, false)).toBe(true);
    expect(nextScreenHeaderScrolled(80, false)).toBe(true);
  });

  it('stays condensed while scroll remains above the expand band', () => {
    expect(nextScreenHeaderScrolled(SCREEN_HEADER_EXPAND_Y + 1, true)).toBe(true);
    expect(nextScreenHeaderScrolled(24, true)).toBe(true);
  });

  it('expands only at or below the expand threshold', () => {
    expect(nextScreenHeaderScrolled(SCREEN_HEADER_EXPAND_Y, true)).toBe(false);
    expect(nextScreenHeaderScrolled(0, true)).toBe(false);
  });

  it('does not flip-flop inside the hysteresis gap', () => {
    const mid = (SCREEN_HEADER_EXPAND_Y + SCREEN_HEADER_COLLAPSE_Y) / 2;
    expect(mid).toBeGreaterThan(SCREEN_HEADER_EXPAND_Y);
    expect(mid).toBeLessThan(SCREEN_HEADER_COLLAPSE_Y);
    expect(nextScreenHeaderScrolled(mid, false)).toBe(false);
    expect(nextScreenHeaderScrolled(mid, true)).toBe(true);
  });
});
