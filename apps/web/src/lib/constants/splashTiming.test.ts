import { describe, expect, it } from 'vitest';
import {
  SPLASH_HOLD_AFTER_MS,
  SPLASH_MIN_MS,
  SPLASH_TILE_COUNT,
  SPLASH_TILE_DURATION_MS,
  SPLASH_TILE_STEP_MS,
  SPLASH_WORD_DELAY_MS,
  SPLASH_WORD_DURATION_MS,
} from './splashTiming';

describe('splashTiming', () => {
  it('holds past the last tile and wordmark keyframes', () => {
    const lastTileEnd = (SPLASH_TILE_COUNT - 1) * SPLASH_TILE_STEP_MS + SPLASH_TILE_DURATION_MS;
    const wordEnd = SPLASH_WORD_DELAY_MS + SPLASH_WORD_DURATION_MS;
    expect(lastTileEnd).toBe(760);
    expect(wordEnd).toBe(780);
    expect(SPLASH_MIN_MS).toBe(Math.max(lastTileEnd, wordEnd) + SPLASH_HOLD_AFTER_MS);
    // Enough rest after the mark settles (previous 850ms felt truncated).
    expect(SPLASH_MIN_MS).toBeGreaterThanOrEqual(1600);
    expect(SPLASH_HOLD_AFTER_MS).toBeGreaterThanOrEqual(800);
  });
});
