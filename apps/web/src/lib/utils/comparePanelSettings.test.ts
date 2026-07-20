import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('$app/environment', () => ({
  browser: true,
}));

import {
  COMPARE_ZOOM_KEY,
  readCompareZoomStage,
  writeCompareZoomStage,
} from './comparePanelSettings';

describe('comparePanelSettings zoom', () => {
  afterEach(() => {
    localStorage.clear();
  });

  it('defaults zoom stage to 2 (7 days)', () => {
    expect(readCompareZoomStage()).toBe(2);
  });

  it('persists and reads a valid zoom stage', () => {
    writeCompareZoomStage(4);
    expect(localStorage.getItem(COMPARE_ZOOM_KEY)).toBe('4');
    expect(readCompareZoomStage()).toBe(4);
  });

  it('falls back to default for invalid stored values', () => {
    localStorage.setItem(COMPARE_ZOOM_KEY, JSON.stringify(99));
    expect(readCompareZoomStage()).toBe(2);
  });
});
