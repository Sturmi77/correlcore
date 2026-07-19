/**
 * App navigation helpers — M3.5 Sprint 1 (ADR-0017).
 *
 * Pure functions so active-state and chrome visibility are unit-testable
 * without mounting the layout.
 */

export type NavMatch = 'exact' | 'prefix';

export interface NavItemConfig {
  href: string;
  labelKey: string;
  match: NavMatch;
  icon: 'home' | 'lightbulb' | 'chart-line' | 'settings';
}

/** Four primary screens — Entry (Screen 2) is a bottom sheet from Home, not a tab. */
export const NAV_ITEMS: readonly NavItemConfig[] = [
  { href: '/', labelKey: 'nav.home', match: 'exact', icon: 'home' },
  { href: '/insights', labelKey: 'nav.insights', match: 'prefix', icon: 'lightbulb' },
  { href: '/trends', labelKey: 'nav.trends', match: 'prefix', icon: 'chart-line' },
  { href: '/settings', labelKey: 'nav.settings', match: 'prefix', icon: 'settings' },
] as const;

/** Exact `/` plus prefixes — anonymous visitors must reach the marketing landing. */
const PUBLIC_ROUTE_PREFIXES = ['/', '/auth', '/status', '/offline', '/privacy', '/impressum'] as const;

/** Routes that hide the app chrome (no bottom / side nav). */
const NO_APP_NAV_PREFIXES = [
  '/auth',
  '/status',
  '/onboarding',
  '/offline',
  '/privacy',
  '/impressum',
] as const;

export function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTE_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

export function isRouteWithoutAppNav(pathname: string): boolean {
  return NO_APP_NAV_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

export function isNavItemActive(pathname: string, href: string, match: NavMatch): boolean {
  if (match === 'exact') {
    return pathname === href;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function shouldShowAppNav(
  authStatus: 'loading' | 'authenticated' | 'anonymous',
  pathname: string
): boolean {
  return authStatus === 'authenticated' && !isRouteWithoutAppNav(pathname);
}
