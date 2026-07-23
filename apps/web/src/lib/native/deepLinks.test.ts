import { describe, expect, it } from 'vitest';
import { loginAwareTarget, resolveDeepLink } from './deepLinks';

describe('resolveDeepLink', () => {
  it('routes the widget entry link through Home so the sheet opens (#447)', () => {
    expect(resolveDeepLink('correlcore://entries/new')).toBe('/?openEntry=1');
  });

  it('accepts a trailing slash', () => {
    expect(resolveDeepLink('correlcore://entries/new/')).toBe('/?openEntry=1');
  });

  it('passes a valid ISO date through as the pre-selected entry date', () => {
    expect(resolveDeepLink('correlcore://entries/new?date=2026-07-23')).toBe(
      '/?openEntry=1&date=2026-07-23'
    );
  });

  it('drops a malformed date instead of forwarding it', () => {
    expect(resolveDeepLink('correlcore://entries/new?date=23.07.2026')).toBe('/?openEntry=1');
    expect(resolveDeepLink('correlcore://entries/new?date=not-a-date')).toBe('/?openEntry=1');
  });

  it('drops dates that match the ISO shape but are not real days', () => {
    // Would otherwise reach fetchDashboardSummary as `as_of` and seed the entry
    // form with an unusable date instead of falling back to today.
    expect(resolveDeepLink('correlcore://entries/new?date=2026-02-30')).toBe('/?openEntry=1');
    expect(resolveDeepLink('correlcore://entries/new?date=2026-99-99')).toBe('/?openEntry=1');
    expect(resolveDeepLink('correlcore://entries/new?date=2026-13-01')).toBe('/?openEntry=1');
    expect(resolveDeepLink('correlcore://entries/new?date=2026-00-10')).toBe('/?openEntry=1');
  });

  it('keeps leap days that really exist', () => {
    expect(resolveDeepLink('correlcore://entries/new?date=2028-02-29')).toBe(
      '/?openEntry=1&date=2028-02-29'
    );
    expect(resolveDeepLink('correlcore://entries/new?date=2026-02-29')).toBe('/?openEntry=1');
  });

  it('ignores foreign schemes so a stray intent cannot navigate the shell', () => {
    expect(resolveDeepLink('https://correlcore.com/entries/new')).toBeNull();
    expect(resolveDeepLink('javascript:alert(1)')).toBeNull();
  });

  it('ignores unknown correlcore paths', () => {
    expect(resolveDeepLink('correlcore://settings')).toBeNull();
    expect(resolveDeepLink('correlcore://entries/edit')).toBeNull();
    expect(resolveDeepLink('correlcore://')).toBeNull();
  });

  it('ignores unparseable input', () => {
    expect(resolveDeepLink('')).toBeNull();
    expect(resolveDeepLink('not a url')).toBeNull();
  });
});

describe('loginAwareTarget', () => {
  it('navigates straight to the sheet when signed in', () => {
    expect(loginAwareTarget('/?openEntry=1', true)).toBe('/?openEntry=1');
  });

  it('preserves the pending entry request through login when signed out', () => {
    // "/" is a public route, so the layout's anonymous guard never fires and
    // the landing login link carries no `next` — without this the request is
    // dropped and the sheet never opens after login.
    expect(loginAwareTarget('/?openEntry=1', false)).toBe('/auth/login?next=%2F%3FopenEntry%3D1');
  });

  it('round-trips through the login page safeNext whitelist', () => {
    const target = loginAwareTarget('/?openEntry=1&date=2026-07-23', false);
    const next = new URL(target, 'https://localhost').searchParams.get('next');
    expect(next).toBe('/?openEntry=1&date=2026-07-23');
    // safeNext rejects non-absolute, protocol-relative and /auth/ targets.
    expect(next?.startsWith('/')).toBe(true);
    expect(next?.startsWith('//')).toBe(false);
    expect(next?.startsWith('/auth/')).toBe(false);
  });
});
