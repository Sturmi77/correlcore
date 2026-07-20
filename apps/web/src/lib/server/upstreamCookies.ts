/**
 * Parse upstream ``Set-Cookie`` lines and apply them via SvelteKit's
 * ``event.cookies`` API (ADR-0011 proxy).
 *
 * Returning raw ``Set-Cookie`` headers from ``handle`` is fragile across
 * Fetch/Headers implementations (multi-value collapse). Applying cookies
 * through ``event.cookies`` is the supported path and survives adapter-node
 * response serialization — without this, login can return 200 while the
 * browser never stores ``access_token``, and later calls like
 * ``/user/me/consents`` fail with ``Could not validate credentials``.
 */

import type { Cookies } from '@sveltejs/kit';

export type ParsedSetCookie = {
  name: string;
  value: string;
  path: string;
  maxAge?: number;
  httpOnly: boolean;
  secure: boolean;
  sameSite: 'strict' | 'lax' | 'none';
};

/** Minimal RFC-6265 attribute parser for our auth-cookie shapes (Max-Age, not Expires). */
export function parseSetCookieLine(line: string): ParsedSetCookie | null {
  const parts = line.split(';').map((part) => part.trim());
  const first = parts[0];
  if (!first) return null;
  const eq = first.indexOf('=');
  if (eq <= 0) return null;

  const parsed: ParsedSetCookie = {
    name: first.slice(0, eq),
    value: first.slice(eq + 1),
    path: '/',
    httpOnly: false,
    secure: false,
    sameSite: 'strict',
  };

  for (const attr of parts.slice(1)) {
    const sep = attr.indexOf('=');
    const key = (sep === -1 ? attr : attr.slice(0, sep)).trim().toLowerCase();
    const val = sep === -1 ? '' : attr.slice(sep + 1).trim();
    if (key === 'path' && val) parsed.path = val;
    else if (key === 'max-age' && val !== '') {
      const n = Number(val);
      if (Number.isFinite(n)) parsed.maxAge = n;
    } else if (key === 'httponly') parsed.httpOnly = true;
    else if (key === 'secure') parsed.secure = true;
    else if (key === 'samesite') {
      const s = val.toLowerCase();
      if (s === 'strict' || s === 'lax' || s === 'none') parsed.sameSite = s;
    }
  }
  return parsed;
}

export function collectSetCookieLines(headers: Headers): string[] {
  const getter = (headers as Headers & { getSetCookie?: () => string[] }).getSetCookie;
  if (typeof getter === 'function') {
    return getter.call(headers);
  }
  const combined = headers.get('set-cookie');
  return combined ? [combined] : [];
}

/** Apply upstream Set-Cookie lines onto the SvelteKit cookies jar. */
export function applyUpstreamCookies(cookies: Cookies, headers: Headers): number {
  let applied = 0;
  for (const line of collectSetCookieLines(headers)) {
    const parsed = parseSetCookieLine(line);
    if (!parsed) continue;
    // Logout / clear_auth_cookies → empty value + Max-Age=0
    if (parsed.maxAge === 0 || parsed.value === '') {
      cookies.delete(parsed.name, { path: parsed.path });
      applied += 1;
      continue;
    }
    cookies.set(parsed.name, parsed.value, {
      path: parsed.path,
      httpOnly: parsed.httpOnly,
      secure: parsed.secure,
      sameSite: parsed.sameSite,
      ...(parsed.maxAge !== undefined ? { maxAge: parsed.maxAge } : {}),
    });
    applied += 1;
  }
  return applied;
}
