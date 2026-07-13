import { browser } from '$app/environment';
import { isOpenEntryRequested } from '$lib/navigation/openEntry';

/** True when the app runs as an installed PWA (standalone display mode). */
export function isStandaloneDisplayMode(): boolean {
  if (!browser) return false;
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

/** Fresh document load (home-screen icon / typed URL), not SPA in-app navigation. */
export function isColdNavigationLaunch(): boolean {
  if (!browser) return false;
  const entry = performance.getEntriesByType('navigation')[0] as
    | PerformanceNavigationTiming
    | undefined;
  return entry?.type === 'navigate';
}

const STANDALONE_HOME_REDIRECT_PREFIXES = ['/dev', '/onboarding'] as const;

/**
 * PWA cold starts should land on Home, not diagnostic/onboarding routes that
 * Firefox can restore from the last session or from stale bookmarks.
 */
export function standaloneLaunchRedirectPath(pathname: string): string | null {
  if (!isStandaloneDisplayMode() || !isColdNavigationLaunch()) return null;
  if (STANDALONE_HOME_REDIRECT_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return '/';
  }
  return null;
}

/** Strip one-shot entry-sheet query params on standalone cold launch at `/`. */
export function shouldStripStandaloneOpenEntryQuery(pathname: string, search: string): boolean {
  if (!isStandaloneDisplayMode() || !isColdNavigationLaunch() || pathname !== '/') return false;
  return isOpenEntryRequested(new URLSearchParams(search));
}

export function stripOpenEntryFromUrl(): void {
  if (!browser) return;
  const url = new URL(window.location.href);
  if (!isOpenEntryRequested(url.searchParams)) return;
  url.searchParams.delete('openEntry');
  url.searchParams.delete('date');
  history.replaceState(history.state, '', `${url.pathname}${url.search}${url.hash}`);
}

export function ensureStandaloneLaunchRoute(navigate: (path: string) => void): void {
  if (!browser) return;

  const redirect = standaloneLaunchRedirectPath(window.location.pathname);
  if (redirect) {
    navigate(redirect);
    return;
  }

  if (shouldStripStandaloneOpenEntryQuery(window.location.pathname, window.location.search)) {
    stripOpenEntryFromUrl();
  }
}
