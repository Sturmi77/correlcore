import { describe, expect, it, vi } from 'vitest';
import { applyUpstreamCookies, collectSetCookieLines, parseSetCookieLine } from './upstreamCookies';

describe('parseSetCookieLine', () => {
  it('parses access cookie with Max-Age and SameSite=strict', () => {
    const parsed = parseSetCookieLine(
      'access_token=eyJ; HttpOnly; Max-Age=900; Path=/api; SameSite=strict'
    );
    expect(parsed).toEqual({
      name: 'access_token',
      value: 'eyJ',
      path: '/api',
      maxAge: 900,
      httpOnly: true,
      secure: false,
      sameSite: 'strict',
    });
  });

  it('parses Secure flag when present', () => {
    const parsed = parseSetCookieLine(
      'refresh_token=eyR; HttpOnly; Secure; Path=/api/v1/auth/refresh; SameSite=strict; Max-Age=2592000'
    );
    expect(parsed?.secure).toBe(true);
    expect(parsed?.path).toBe('/api/v1/auth/refresh');
    expect(parsed?.maxAge).toBe(2592000);
  });

  it('returns null for garbage', () => {
    expect(parseSetCookieLine('')).toBeNull();
    expect(parseSetCookieLine('=novalue')).toBeNull();
  });
});

describe('applyUpstreamCookies', () => {
  it('sets access + refresh via cookies API and clears Max-Age=0', () => {
    const set = vi.fn();
    const del = vi.fn();
    const cookies = { set, delete: del } as unknown as Parameters<typeof applyUpstreamCookies>[0];
    const headers = new Headers();
    headers.append(
      'set-cookie',
      'access_token=eyJ; HttpOnly; Max-Age=900; Path=/api; SameSite=strict'
    );
    headers.append(
      'set-cookie',
      'refresh_token=; HttpOnly; Max-Age=0; Path=/api/v1/auth/refresh; SameSite=strict'
    );

    const n = applyUpstreamCookies(cookies, headers);
    expect(n).toBe(2);
    expect(set).toHaveBeenCalledWith(
      'access_token',
      'eyJ',
      expect.objectContaining({
        path: '/api',
        httpOnly: true,
        secure: false,
        sameSite: 'strict',
        maxAge: 900,
      })
    );
    expect(del).toHaveBeenCalledWith('refresh_token', { path: '/api/v1/auth/refresh' });
  });
});

describe('collectSetCookieLines', () => {
  it('uses getSetCookie when available', () => {
    const headers = {
      getSetCookie: () => ['a=1', 'b=2'],
      get: () => null,
    } as unknown as Headers;
    expect(collectSetCookieLines(headers)).toEqual(['a=1', 'b=2']);
  });
});
