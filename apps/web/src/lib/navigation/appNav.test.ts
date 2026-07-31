import { describe, expect, it } from 'vitest';
import {
  isMarketingLandingView,
  isNavItemActive,
  isPublicRoute,
  isRouteWithoutAppNav,
  shouldShowAppNav,
} from './appNav';

describe('appNav routing helpers', () => {
  describe('isPublicRoute', () => {
    it('treats home, auth, status, offline, privacy, and impressum as public', () => {
      expect(isPublicRoute('/')).toBe(true);
      expect(isPublicRoute('/auth/login')).toBe(true);
      expect(isPublicRoute('/status')).toBe(true);
      expect(isPublicRoute('/offline')).toBe(true);
      expect(isPublicRoute('/privacy')).toBe(true);
      expect(isPublicRoute('/impressum')).toBe(true);
      expect(isPublicRoute('/insights')).toBe(false);
      expect(isPublicRoute('/settings')).toBe(false);
    });
  });

  describe('isRouteWithoutAppNav', () => {
    it('hides nav on auth, status, onboarding, offline, privacy, and impressum', () => {
      expect(isRouteWithoutAppNav('/auth/register')).toBe(true);
      expect(isRouteWithoutAppNav('/onboarding/profile')).toBe(true);
      expect(isRouteWithoutAppNav('/offline')).toBe(true);
      expect(isRouteWithoutAppNav('/privacy')).toBe(true);
      expect(isRouteWithoutAppNav('/impressum')).toBe(true);
      expect(isRouteWithoutAppNav('/insights')).toBe(false);
      expect(isRouteWithoutAppNav('/dev')).toBe(false);
    });
  });

  describe('shouldShowAppNav', () => {
    it('shows nav only for authenticated app routes', () => {
      expect(shouldShowAppNav('authenticated', '/')).toBe(true);
      expect(shouldShowAppNav('authenticated', '/settings/tags')).toBe(true);
      expect(shouldShowAppNav('authenticated', '/auth/login')).toBe(false);
      expect(shouldShowAppNav('authenticated', '/offline')).toBe(false);
      expect(shouldShowAppNav('anonymous', '/')).toBe(false);
      expect(shouldShowAppNav('loading', '/insights')).toBe(false);
    });

    it('hides nav on authenticated landing preview (#588)', () => {
      const params = new URLSearchParams('landing=1');
      expect(shouldShowAppNav('authenticated', '/', params)).toBe(false);
    });
  });

  describe('isMarketingLandingView', () => {
    it('shows marketing landing for anonymous home and ?landing=1 preview', () => {
      expect(isMarketingLandingView('anonymous', '/')).toBe(true);
      expect(isMarketingLandingView('authenticated', '/')).toBe(false);
      expect(
        isMarketingLandingView('authenticated', '/', new URLSearchParams('landing=1'))
      ).toBe(true);
      expect(isMarketingLandingView('authenticated', '/insights')).toBe(false);
    });
  });

  describe('isNavItemActive', () => {
    it('matches home exactly', () => {
      expect(isNavItemActive('/', '/', 'exact')).toBe(true);
      expect(isNavItemActive('/entries/new', '/', 'exact')).toBe(false);
    });

    it('matches insights and settings by prefix', () => {
      expect(isNavItemActive('/insights', '/insights', 'prefix')).toBe(true);
      expect(isNavItemActive('/insights/disclaimer', '/insights', 'prefix')).toBe(true);
      expect(isNavItemActive('/settings/tags', '/settings', 'prefix')).toBe(true);
      expect(isNavItemActive('/trend', '/trends', 'prefix')).toBe(false);
    });
  });
});
