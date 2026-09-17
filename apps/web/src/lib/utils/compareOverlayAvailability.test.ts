import { describe, expect, it } from 'vitest';
import {
  EMPTY_COMPARE_OVERLAY_AVAILABILITY,
  MIN_OVERLAY_PINS,
  shouldShowOverlayPinHint,
  type CompareOverlayAvailability,
} from './compareOverlayAvailability';

const ready: CompareOverlayAvailability = { pinnedCount: 2, coincidence: true, lag1: true };

describe('shouldShowOverlayPinHint (#919)', () => {
  it('nudges once a second pin opens the coincidence gate', () => {
    expect(MIN_OVERLAY_PINS).toBe(2);
    expect(shouldShowOverlayPinHint(ready, false, false)).toBe(true);
  });

  it('stays silent below the pin minimum', () => {
    expect(shouldShowOverlayPinHint(EMPTY_COMPARE_OVERLAY_AVAILABILITY, false, false)).toBe(false);
    expect(
      shouldShowOverlayPinHint({ pinnedCount: 1, coincidence: false, lag1: false }, false, false)
    ).toBe(false);
  });

  it('stays silent when the gate is closed despite enough pins', () => {
    expect(
      shouldShowOverlayPinHint({ pinnedCount: 3, coincidence: false, lag1: true }, false, false)
    ).toBe(false);
  });

  it('stays silent once the overlay is already on', () => {
    expect(shouldShowOverlayPinHint(ready, true, false)).toBe(false);
  });

  it('stays silent after dismissal', () => {
    expect(shouldShowOverlayPinHint(ready, false, true)).toBe(false);
  });
});
