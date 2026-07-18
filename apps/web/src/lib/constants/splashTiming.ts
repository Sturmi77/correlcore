/**
 * Brand boot splash timing — shared by CorrelCoreSplash CSS and +layout hold.
 *
 * Tile cascade: 9 tiles, delay i * TILE_STEP_MS, each TILE_DURATION_MS.
 * Wordmark: WORD_DELAY_MS + WORD_DURATION_MS.
 * After the last keyframe ends, HOLD_AFTER_MS keeps the settled mark on screen
 * so the boot does not feel like a one-frame flash on fast devices.
 */

export const SPLASH_TILE_STEP_MS = 55;
export const SPLASH_TILE_DURATION_MS = 320;
export const SPLASH_TILE_COUNT = 9;

export const SPLASH_WORD_DELAY_MS = 520;
export const SPLASH_WORD_DURATION_MS = 260;

/** Quiet beat after tiles + wordmark have finished animating in. */
export const SPLASH_HOLD_AFTER_MS = 900;

const splashAnimationEndMs = Math.max(
  (SPLASH_TILE_COUNT - 1) * SPLASH_TILE_STEP_MS + SPLASH_TILE_DURATION_MS,
  SPLASH_WORD_DELAY_MS + SPLASH_WORD_DURATION_MS
);

/** Minimum splash mount time when prefers-reduced-motion is off. */
export const SPLASH_MIN_MS = splashAnimationEndMs + SPLASH_HOLD_AFTER_MS;
