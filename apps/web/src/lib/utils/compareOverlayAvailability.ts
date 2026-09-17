/**
 * Compare overlay gate state (#919).
 *
 * The A∩B / Lag-1 gates are derived from the pinned heatmap rows, which only
 * TrendsComparePanel holds. The mobile settings sheet renders the same toggles
 * and needs the gate without re-deriving it, so the panel publishes this.
 */
export type CompareOverlayAvailability = {
  pinnedCount: number;
  coincidence: boolean;
  lag1: boolean;
};

export const EMPTY_COMPARE_OVERLAY_AVAILABILITY: CompareOverlayAvailability = {
  pinnedCount: 0,
  coincidence: false,
  lag1: false,
};

/** Minimum pins before either overlay can say anything (#908 / #910). */
export const MIN_OVERLAY_PINS = 2;

/**
 * The one-time nudge fires only when highlighting would actually do something:
 * enough pins, an open gate, and the overlay still off.
 */
export function shouldShowOverlayPinHint(
  availability: CompareOverlayAvailability,
  coincidenceHighlight: boolean,
  dismissed: boolean
): boolean {
  if (dismissed || coincidenceHighlight) return false;
  return availability.pinnedCount >= MIN_OVERLAY_PINS && availability.coincidence;
}
