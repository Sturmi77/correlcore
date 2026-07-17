/**
 * Tests for the SvelteKit `handle` hook that proxies `/api/*` to the
 * internal API container (ADR-0011).
 *
 * Coverage focus:
 *   - Non-`/api/*` requests fall through to `resolve()` untouched.
 *   - `/api/*` requests are forwarded to `INTERNAL_API_URL` (default
 *     `http://api:8000`) with method, path, query string and JSON body
 *     preserved verbatim.
 *   - Hop-by-hop headers (`connection`, `transfer-encoding`, …) are
 *     stripped on both directions.
 *   - The upstream `Set-Cookie` header (HttpOnly auth cookies) is
 *     forwarded to the browser unchanged.
 *   - Upstream connection failures are translated into a JSON 502.
 *   - GET requests do not carry a body or a `duplex` option to the
 *     upstream fetch.
 */

import type { Handle, RequestEvent } from '@sveltejs/kit';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('$lib/observability/errorTracking.server', () => ({
  initServerErrorTracking: vi.fn(),
  captureServerException: vi.fn(),
}));

import { handle } from './hooks.server';

type FetchMock = ReturnType<typeof vi.fn>;
type ResolveFn = Parameters<Handle>[0]['resolve'];

function makeEvent(url: string, init: RequestInit = {}): RequestEvent {
  const request = new Request(url, init);
  // Only the fields the hook actually reads. Everything else can stay
  // undefined — the Handle type is structurally a function, the runtime
  // signature is `({ event, resolve })`.
  return {
    url: new URL(url),
    request,
    getClientAddress: () => '203.0.113.42',
  } as unknown as RequestEvent;
}

let fetchMock: FetchMock;
/** Vitest 4 mock + Handle.resolve — cast once so svelte-check accepts call sites. */
let resolveMock: ReturnType<typeof vi.fn> & ResolveFn;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
  resolveMock = vi.fn().mockResolvedValue(new Response('app shell')) as typeof resolveMock;
  delete process.env.INTERNAL_API_URL;
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('handle — pass-through for non-API paths', () => {
  it('falls through to resolve() for /', async () => {
    const event = makeEvent('http://web.local/');
    await handle({ event, resolve: resolveMock });
    expect(resolveMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('falls through for static assets', async () => {
    const event = makeEvent('http://web.local/_app/immutable/x.js');
    await handle({ event, resolve: resolveMock });
    expect(resolveMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('does not match a path that merely contains /api/ later', async () => {
    const event = makeEvent('http://web.local/docs/api/whatever');
    await handle({ event, resolve: resolveMock });
    expect(resolveMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('handle — proxy /api/*', () => {
  it('forwards GET to INTERNAL_API_URL with path and query string', async () => {
    fetchMock.mockResolvedValue(new Response('{"ok":true}', { status: 200 }));
    const event = makeEvent('http://web.local/api/v1/health/ready?verbose=1');

    const res = await handle({ event, resolve: resolveMock });

    expect(resolveMock).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('http://api:8000/api/v1/health/ready?verbose=1');
    expect((init as RequestInit).method).toBe('GET');
    expect((init as RequestInit).body).toBeUndefined();
    expect((init as RequestInit & { duplex?: string }).duplex).toBeUndefined();
    expect(res.status).toBe(200);
    expect(await res.text()).toBe('{"ok":true}');
  });

  it('honours INTERNAL_API_URL override and strips a trailing slash', async () => {
    process.env.INTERNAL_API_URL = 'http://api-prod:9000/';
    fetchMock.mockResolvedValue(new Response('{}', { status: 200 }));

    const event = makeEvent('http://web.local/api/v1/ping');
    await handle({ event, resolve: resolveMock });

    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe('http://api-prod:9000/api/v1/ping');
  });

  it('forwards POST with JSON body and content-type header', async () => {
    fetchMock.mockResolvedValue(
      new Response('{"access_token":"eyJ"}', {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    );
    const event = makeEvent('http://web.local/api/v1/auth/login', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ email: 'a@b.de', password: 'pw' }),
    });

    await handle({ event, resolve: resolveMock });

    const [, init] = fetchMock.mock.calls[0];
    const i = init as RequestInit & { duplex?: string };
    expect(i.method).toBe('POST');
    expect(i.duplex).toBe('half');
    expect((i.headers as Headers).get('content-type')).toBe('application/json');
    expect((i.headers as Headers).get('host')).toBe('api:8000');
  });

  it('strips hop-by-hop request headers before forwarding', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    const event = makeEvent('http://web.local/api/v1/ping', {
      headers: {
        connection: 'keep-alive',
        'keep-alive': 'timeout=5',
        'transfer-encoding': 'chunked',
        'x-trace-id': 'abc123',
      },
    });

    await handle({ event, resolve: resolveMock });

    const [, init] = fetchMock.mock.calls[0];
    const headers = (init as RequestInit).headers as Headers;
    expect(headers.get('connection')).toBeNull();
    expect(headers.get('keep-alive')).toBeNull();
    expect(headers.get('transfer-encoding')).toBeNull();
    expect(headers.get('x-trace-id')).toBe('abc123');
  });

  it('overwrites client supplied forwarding headers', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    const event = makeEvent('http://web.local/api/v1/ping', {
      headers: {
        'x-forwarded-for': '198.51.100.99',
        'x-real-ip': '198.51.100.100',
      },
    });

    await handle({ event, resolve: resolveMock });

    const [, init] = fetchMock.mock.calls[0];
    const headers = (init as RequestInit).headers as Headers;
    expect(headers.get('x-forwarded-for')).toBe('203.0.113.42');
    expect(headers.get('x-forwarded-host')).toBe('web.local');
    expect(headers.get('x-forwarded-proto')).toBe('http');
    expect(headers.get('x-real-ip')).toBe('203.0.113.42');
  });

  it('forwards upstream Set-Cookie (HttpOnly auth cookie) verbatim', async () => {
    const upstreamHeaders = new Headers();
    upstreamHeaders.append(
      'set-cookie',
      'access_token=eyJ; HttpOnly; Secure; SameSite=Strict; Path=/api'
    );
    upstreamHeaders.append(
      'set-cookie',
      'refresh_token=eyR; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/refresh'
    );
    upstreamHeaders.set('content-type', 'application/json');
    fetchMock.mockResolvedValue(
      new Response('{"access_token":"eyJ","expires_in":1800}', {
        status: 200,
        headers: upstreamHeaders,
      })
    );

    const event = makeEvent('http://web.local/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({}),
    });
    const res = await handle({ event, resolve: resolveMock });

    expect(res.status).toBe(200);
    // jsdom and Node's undici expose multiple Set-Cookie headers slightly
    // differently — some give one comma-joined string from `.get()`, others
    // expose a `getSetCookie()` method that returns an array. Accept both.
    const setCookieRaw =
      (res.headers as Headers & { getSetCookie?: () => string[] }).getSetCookie?.() ??
      (res.headers.get('set-cookie') ? [res.headers.get('set-cookie') as string] : []);
    const joined = setCookieRaw.join(' || ');
    expect(joined).toContain('access_token=eyJ');
    expect(joined).toContain('refresh_token=eyR');
    expect(joined).toContain('HttpOnly');
    expect(joined).toContain('SameSite=Strict');
  });

  it('returns a JSON 502 when the upstream fetch throws', async () => {
    fetchMock.mockRejectedValue(new Error('ECONNREFUSED'));
    const event = makeEvent('http://web.local/api/v1/health/live');

    const res = await handle({ event, resolve: resolveMock });

    expect(res.status).toBe(502);
    expect(res.headers.get('content-type')).toBe('application/json');
    const body = await res.json();
    expect(body).toEqual({ detail: 'Upstream API unreachable' });
  });

  it('forwards upstream non-2xx (4xx/5xx) status untouched', async () => {
    fetchMock.mockResolvedValue(
      new Response('{"detail":"Invalid email or password"}', {
        status: 401,
        headers: { 'content-type': 'application/json' },
      })
    );
    const event = makeEvent('http://web.local/api/v1/auth/login', {
      method: 'POST',
    });

    const res = await handle({ event, resolve: resolveMock });

    expect(res.status).toBe(401);
    const body = await res.json();
    expect(body).toEqual({ detail: 'Invalid email or password' });
  });
});
