import { describe, expect, it } from 'vitest';
import {
  isNavItemActive,
  isPublicRoute,
  isRouteWithoutAppNav,
  shouldShowAppNav,
} from './appNav';

describe('appNav routing helpers', () => {
  describe('isPublicRoute', () => {
    it('treats auth and status as public', () => {
      expect(isPublicRoute('/auth/login')).toBe(true);
      expect(isPublicRoute('/status')).toBe(true);
      expect(isPublicRoute('/')).toBe(false);
    });
  });

  describe('isRouteWithoutAppNav', () => {
    it('hides nav on auth, status, and onboarding', () => {
      expect(isRouteWithoutAppNav('/auth/register')).toBe(true);
      expect(isRouteWithoutAppNav('/onboarding/profile')).toBe(true);
      expect(isRouteWithoutAppNav('/insights')).toBe(false);
      expect(isRouteWithoutAppNav('/dev')).toBe(false);
    });
  });

  describe('shouldShowAppNav', () => {
    it('shows nav only for authenticated app routes', () => {
      expect(shouldShowAppNav('authenticated', '/')).toBe(true);
      expect(shouldShowAppNav('authenticated', '/settings/tags')).toBe(true);
      expect(shouldShowAppNav('authenticated', '/auth/login')).toBe(false);
      expect(shouldShowAppNav('anonymous', '/')).toBe(false);
      expect(shouldShowAppNav('loading', '/insights')).toBe(false);
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
