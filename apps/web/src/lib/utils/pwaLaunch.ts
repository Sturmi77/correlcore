import { browser } from '$app/environment';
import { isOpenEntryRequested } from '$lib/navigation/openEntry';

/** True when the app runs as an installed PWA (standalone display mode). */
export function isStandaloneDisplayMode(): boolean {
  if (!browser) return false;
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    window.matchMedia('(display-mode: fullscreen)').matches ||
    window.matchMedia('(display-mode: minimal-ui)').matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

/**
 * Document load that should normalize the homescreen entry route.
 *
 * Includes `reload` (and a missing Performance entry): Firefox often restores
 * the last standalone session as a reload, not a fresh `navigate`. SPA
 * in-app navigations do not remount the root layout, so broadening this for
 * document loads is safe.
 */
export function isColdNavigationLaunch(): boolean {
  if (!browser) return false;
  const entry = performance.getEntriesByType('navigation')[0] as
    PerformanceNavigationTiming | undefined;
  if (!entry) return true;
  return entry.type === 'navigate' || entry.type === 'reload';
}

const STANDALONE_HOME_REDIRECT_PREFIXES = ['/dev', '/onboarding'] as const;

/**
 * PWA document loads should land on Home, not diagnostic/onboarding routes that
 * Firefox can restore from the last session or from stale bookmarks.
 */
export function standaloneLaunchRedirectPath(pathname: string): string | null {
  if (!isStandaloneDisplayMode() || !isColdNavigationLaunch()) return null;
  if (STANDALONE_HOME_REDIRECT_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return '/';
  }
  return null;
}

/** Strip one-shot entry-sheet query params on standalone document load at `/`. */
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
