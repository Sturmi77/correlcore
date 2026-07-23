import { describe, expect, it } from 'vitest';
import { resolveDeepLink } from './deepLinks';

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
