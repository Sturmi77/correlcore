import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  isColdNavigationLaunch,
  isStandaloneDisplayMode,
  shouldStripStandaloneOpenEntryQuery,
  standaloneLaunchRedirectPath,
} from './pwaLaunch';

describe('pwaLaunch', () => {
  beforeEach(() => {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: query === '(display-mode: standalone)',
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    Object.defineProperty(window.navigator, 'standalone', {
      configurable: true,
      value: false,
    });
    vi.stubGlobal('performance', {
      getEntriesByType: vi.fn(() => [{ type: 'navigate' }]),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('detects standalone display mode', () => {
    expect(isStandaloneDisplayMode()).toBe(true);
  });

  it('redirects standalone cold launches away from /dev', () => {
    expect(standaloneLaunchRedirectPath('/dev')).toBe('/');
    expect(standaloneLaunchRedirectPath('/onboarding/profile')).toBe('/');
    expect(standaloneLaunchRedirectPath('/')).toBeNull();
    expect(standaloneLaunchRedirectPath('/settings')).toBeNull();
  });

  it('redirects Firefox session restores that report reload', () => {
    vi.stubGlobal('performance', {
      getEntriesByType: vi.fn(() => [{ type: 'reload' }]),
    });
    expect(isColdNavigationLaunch()).toBe(true);
    expect(standaloneLaunchRedirectPath('/dev')).toBe('/');
    expect(shouldStripStandaloneOpenEntryQuery('/', '?openEntry=1')).toBe(true);
  });

  it('treats a missing PerformanceNavigationTiming entry as a document launch', () => {
    vi.stubGlobal('performance', {
      getEntriesByType: vi.fn(() => []),
    });
    expect(isColdNavigationLaunch()).toBe(true);
    expect(standaloneLaunchRedirectPath('/onboarding')).toBe('/');
  });

  it('does not redirect back_forward history restores', () => {
    vi.stubGlobal('performance', {
      getEntriesByType: vi.fn(() => [{ type: 'back_forward' }]),
    });
    expect(standaloneLaunchRedirectPath('/dev')).toBeNull();
    expect(isColdNavigationLaunch()).toBe(false);
  });

  it('strips stale openEntry query on standalone cold launch at home', () => {
    expect(shouldStripStandaloneOpenEntryQuery('/', '?openEntry=1')).toBe(true);
    expect(shouldStripStandaloneOpenEntryQuery('/', '')).toBe(false);
    expect(shouldStripStandaloneOpenEntryQuery('/insights', '?openEntry=1')).toBe(false);
  });
});
