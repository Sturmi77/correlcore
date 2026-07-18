/**
 * Tests for the central API client (Issue #40).
 *
 * Focus areas:
 *   - 2xx happy path returns parsed JSON
 *   - 4xx throws ApiError with parsed detail
 *   - Network failure throws NetworkError
 *   - 401 triggers exactly one /auth/refresh, then replays original request
 *   - Concurrent 401s share the same refresh promise (single-flight)
 *   - skipAuthRefresh prevents the retry loop on /auth/refresh itself
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, NetworkError, apiFetch, redactUrlCredentials } from './client';

type FetchMock = ReturnType<typeof vi.fn>;

function jsonResponse(body: unknown, init: ResponseInit = { status: 200 }): Response {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  });
}

function emptyResponse(status: number): Response {
  return new Response(null, { status });
}

let fetchMock: FetchMock;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('apiFetch — happy path', () => {
  it('parses JSON 200 responses', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ hello: 'world' }));
    const data = await apiFetch<{ hello: string }>('/ping');
    expect(data).toEqual({ hello: 'world' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('returns undefined for 204 No Content', async () => {
    fetchMock.mockResolvedValueOnce(emptyResponse(204));
    const data = await apiFetch('/things', { method: 'DELETE' });
    expect(data).toBeUndefined();
  });

  it('serialises json option and sets headers', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ ok: true }));
    await apiFetch('/auth/login', { method: 'POST', json: { email: 'a@b.de' } });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe('POST');
    expect(init.body).toBe(JSON.stringify({ email: 'a@b.de' }));
    expect(init.credentials).toBe('include');
    expect((init.headers as Headers).get('Content-Type')).toBe('application/json');
  });
});

describe('apiFetch — error handling', () => {
  it('throws ApiError on 4xx with parsed detail', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'invalid input' }, { status: 400 }));
    await expect(apiFetch('/foo')).rejects.toMatchObject({
      name: 'ApiError',
      status: 400,
      detail: 'invalid input',
    });
  });

  it('throws ApiError with statusText when body is not JSON', async () => {
    fetchMock.mockResolvedValueOnce(new Response('boom', { status: 500, statusText: 'Server' }));
    await expect(apiFetch('/foo')).rejects.toBeInstanceOf(ApiError);
  });

  it('throws NetworkError when fetch rejects', async () => {
    fetchMock.mockRejectedValueOnce(new Error('offline'));
    await expect(apiFetch('/foo')).rejects.toBeInstanceOf(NetworkError);
  });

  it('includes API base and cause message on NetworkError', async () => {
    fetchMock.mockRejectedValueOnce(new Error('Mixed Content blocked'));
    try {
      await apiFetch('/auth/login');
      expect.unreachable('expected NetworkError');
    } catch (err) {
      expect(err).toBeInstanceOf(NetworkError);
      const networkErr = err as NetworkError;
      expect(networkErr.apiBase).toBeTruthy();
      expect(networkErr.message).toContain('Mixed Content blocked');
      expect(networkErr.message).toContain(String(networkErr.apiBase));
    }
  });

  it('redacts URL credentials from NetworkError messages', () => {
    const err = new NetworkError(
      '/auth/login',
      new Error('failed'),
      'https://user:s3cret@api.example/api/v1'
    );
    expect(err.apiBase).toBe('https://api.example/api/v1');
    expect(err.message).toContain('https://api.example/api/v1');
    expect(err.message).not.toContain('s3cret');
    expect(err.message).not.toContain('user:');
  });
});

describe('redactUrlCredentials', () => {
  it('strips userinfo from absolute URLs', () => {
    expect(redactUrlCredentials('https://alice:pw@host.example/api/v1')).toBe(
      'https://host.example/api/v1'
    );
  });

  it('leaves relative bases unchanged', () => {
    expect(redactUrlCredentials('/api/v1')).toBe('/api/v1');
  });
});

describe('apiFetch — single-flight refresh', () => {
  it('retries once after a successful /auth/refresh', async () => {
    // 1st call to /protected → 401
    // 2nd call (refresh) → 200
    // 3rd call to /protected (replay) → 200 with payload
    fetchMock
      .mockResolvedValueOnce(emptyResponse(401))
      .mockResolvedValueOnce(jsonResponse({ ok: true }))
      .mockResolvedValueOnce(jsonResponse({ data: 'after-refresh' }));

    const result = await apiFetch<{ data: string }>('/protected');

    expect(result).toEqual({ data: 'after-refresh' });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toContain('/auth/refresh');
  });

  it('does not retry when refresh itself fails', async () => {
    fetchMock.mockResolvedValueOnce(emptyResponse(401)).mockResolvedValueOnce(emptyResponse(401)); // refresh also unauth

    await expect(apiFetch('/protected')).rejects.toMatchObject({
      name: 'ApiError',
      status: 401,
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('shares a single refresh between concurrent 401s', async () => {
    // Two parallel requests both hit 401.
    // We expect ONE /auth/refresh, then both originals replayed.
    fetchMock.mockImplementation((url: string) => {
      if (url.includes('/auth/refresh')) {
        return Promise.resolve(jsonResponse({ ok: true }));
      }
      // First call to each path returns 401, second returns 200.
      const callCount = fetchMock.mock.calls.filter((c) => c[0] === url).length;
      if (callCount === 1) return Promise.resolve(emptyResponse(401));
      return Promise.resolve(jsonResponse({ url }));
    });

    const [a, b] = await Promise.all([apiFetch('/a'), apiFetch('/b')]);
    expect(a).toEqual({ url: expect.stringContaining('/a') });
    expect(b).toEqual({ url: expect.stringContaining('/b') });

    const refreshCalls = fetchMock.mock.calls.filter((c) => String(c[0]).includes('/auth/refresh'));
    expect(refreshCalls).toHaveLength(1);
  });

  it('skipAuthRefresh prevents the retry path', async () => {
    fetchMock.mockResolvedValueOnce(emptyResponse(401));
    await expect(apiFetch('/auth/refresh', { skipAuthRefresh: true })).rejects.toMatchObject({
      status: 401,
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe('apiFetch — Capacitor Bearer path', () => {
  beforeEach(async () => {
    vi.resetModules();
    vi.doMock('./platform', () => ({
      isCapacitorBuild: () => true,
      usesBearerAuth: () => true,
    }));
    const tokens = await import('./sessionTokens');
    tokens._resetSessionTokensForTests();
    tokens.setSessionTokens({
      access_token: 'access-1',
      refresh_token: 'refresh-1',
    });
  });

  afterEach(async () => {
    vi.doUnmock('./platform');
    vi.resetModules();
  });

  it('sends Authorization Bearer and omits cookies', async () => {
    const { apiFetch: bearerFetch } = await import('./client');
    fetchMock.mockResolvedValueOnce(jsonResponse({ ok: true }));
    await bearerFetch('/me', { credentials: 'include' });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.credentials).toBe('omit');
    expect((init.headers as Headers).get('Authorization')).toBe('Bearer access-1');
  });

  it('refreshes with body refresh_token and rotates in-memory access', async () => {
    const { apiFetch: bearerFetch } = await import('./client');
    const { getAccessToken } = await import('./sessionTokens');
    fetchMock
      .mockResolvedValueOnce(emptyResponse(401))
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: 'access-2',
          refresh_token: 'refresh-2',
          token_type: 'bearer',
          expires_in: 900,
          user: { id: 'u1', email: 'a@b.de', display_name: null, is_verified: true },
        })
      )
      .mockResolvedValueOnce(jsonResponse({ data: 'ok' }));

    const result = await bearerFetch<{ data: string }>('/protected');
    expect(result).toEqual({ data: 'ok' });
    expect(String(fetchMock.mock.calls[1][0])).toContain('include_access_token=true');
    expect(fetchMock.mock.calls[1][1].body).toBe(JSON.stringify({ refresh_token: 'refresh-1' }));
    expect(getAccessToken()).toBe('access-2');
    const replayHeaders = fetchMock.mock.calls[2][1].headers as Headers;
    expect(replayHeaders.get('Authorization')).toBe('Bearer access-2');
  });
});
