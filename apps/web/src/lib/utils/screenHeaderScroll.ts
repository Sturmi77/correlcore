/**
 * Sticky ScreenHeader scroll hysteresis (#851).
 *
 * A single threshold flips expanded ↔ condensed when sticky chrome height
 * changes feed back into scrollTop. Collapse and expand use separate bands so
 * partial scrolls near the edge do not oscillate.
 */

/** ScrollY (px) at/above which the header enters the condensed state. */
export const SCREEN_HEADER_COLLAPSE_Y = 32;

/** ScrollY (px) at/below which a condensed header expands again. */
export const SCREEN_HEADER_EXPAND_Y = 8;

/**
 * Next `scrolled` flag given current scroll offset and previous state.
 * Pure helper so unit tests cover the band without DOM scroll wiring.
 */
export function nextScreenHeaderScrolled(y: number, currentlyScrolled: boolean): boolean {
  if (currentlyScrolled) {
    return y > SCREEN_HEADER_EXPAND_Y;
  }
  return y >= SCREEN_HEADER_COLLAPSE_Y;
}
