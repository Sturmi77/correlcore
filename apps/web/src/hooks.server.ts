/**
 * Server-side request hook for SvelteKit (adapter-node).
 *
 * Implements ADR-0011: internal reverse proxy in the web container.
 *
 * Background
 * ----------
 * The browser bundle calls the API via the relative path `/api/v1/...`
 * (see `apps/web/src/lib/api/client.ts` — `API_BASE` defaults to `/api/v1`).
 * Without a reverse proxy in front of the web container, those requests
 * land at the SvelteKit Node server, which has no route for `/api/*` and
 * returns a 404. This hook catches every `/api/*` request and forwards it
 * to the API container reachable at `INTERNAL_API_URL` (default
 * `http://api:8000`).
 *
 * Why this is the right place
 * ---------------------------
 * - `VITE_API_BASE_URL` is a build-time constant baked into the JS bundle.
 *   Any deployment topology that does not happen to match the URL chosen
 *   at build time breaks. With this proxy, the bundle always uses
 *   `/api/v1` (same-origin) and the operator only configures the
 *   server-side `INTERNAL_API_URL` env at runtime — no rebuilds for
 *   different hosts/ports.
 * - Same-origin requests keep `SameSite=Strict` cookies working without
 *   any additional CORS plumbing (see ADR-0006).
 * - Closing the API port at the container boundary becomes possible:
 *   only the web container needs to be reachable from outside, and the
 *   API can stay on the docker-internal network via `expose:`.
 *
 * Behaviour
 * ---------
 * - Only requests whose pathname starts with `/api/` are proxied.
 * - All other requests fall through to SvelteKit's normal `resolve()`.
 * - Method, headers, body and the trailing pathname (incl. query string)
 *   are forwarded verbatim. Hop-by-hop headers (`connection`, …) are
 *   stripped per RFC 7230 §6.1.
 * - The upstream `Set-Cookie` header is preserved untouched so the
 *   HttpOnly auth cookies set by the API reach the browser unchanged.
 * - On upstream connection failure a 502 is returned with a short JSON
 *   body so the SPA's `apiFetch` surface still parses an error.
 *
 * Configuration
 * -------------
 * - `INTERNAL_API_URL` — base URL of the API container. Defaults to
 *   `http://api:8000` which matches the docker-compose service name.
 *   Override only when the API runs under a different hostname inside
 *   the container network.
 *
 * NOTE: `import.meta.env.VITE_API_BASE_URL` is intentionally not read
 * here. This proxy makes the bundle topology-agnostic by relying on the
 * relative `/api/v1` default; injecting a different base URL at build
 * time would defeat the purpose of the proxy.
 */

import type { Handle } from '@sveltejs/kit';

// Hop-by-hop headers per RFC 7230 §6.1 — never forwarded by a proxy.
const HOP_BY_HOP_HEADERS = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
]);

function getInternalApiUrl(): string {
  // process.env is fine here — adapter-node runs in Node, not in the
  // browser. We deliberately do not read VITE_* vars (build-time only).
  const raw = process.env.INTERNAL_API_URL ?? 'http://api:8000';
  // Strip a trailing slash so concatenation with `/api/...` is unambiguous.
  return raw.replace(/\/+$/, '');
}

function stripHopByHop(headers: Headers): Headers {
  const out = new Headers();
  // `Set-Cookie` is the only header where multiple values must NOT be
  // collapsed into one comma-joined string — cookies legitimately contain
  // commas (e.g. `Expires=Wed, 21 Oct 2026 07:28:00 GMT`). Iterating with
  // `headers.entries()` yields the joined form, which would corrupt
  // multi-value `Set-Cookie`. So we lift `set-cookie` out via
  // `getSetCookie()` (Node 18+, undici, latest jsdom) and copy it as
  // separate appends, then iterate everything else normally.
  const setCookieGetter = (headers as Headers & { getSetCookie?: () => string[] }).getSetCookie;
  if (typeof setCookieGetter === 'function') {
    for (const cookie of setCookieGetter.call(headers)) {
      out.append('set-cookie', cookie);
    }
  } else {
    // Fallback for environments without getSetCookie. The browser's
    // Headers.entries() collapses multiple Set-Cookie values, so this
    // path is best-effort: a single combined value is forwarded as-is.
    const combined = headers.get('set-cookie');
    if (combined) out.append('set-cookie', combined);
  }

  for (const [key, value] of headers.entries()) {
    const lower = key.toLowerCase();
    if (HOP_BY_HOP_HEADERS.has(lower)) continue;
    if (lower === 'set-cookie') continue; // already handled above
    out.append(key, value);
  }
  return out;
}

export const handle: Handle = async ({ event, resolve }) => {
  const { pathname, search } = event.url;

  if (!pathname.startsWith('/api/')) {
    return resolve(event);
  }

  const upstreamBase = getInternalApiUrl();
  const upstreamUrl = `${upstreamBase}${pathname}${search}`;

  const forwardedHeaders = stripHopByHop(event.request.headers);
  // The Host header would point at the web container's vhost; replace it
  // with the upstream host so virtual-host routing on the API side (if
  // any) works as expected. URL parsing handles default ports correctly.
  forwardedHeaders.set('host', new URL(upstreamBase).host);
  // Do not pass through browser-supplied forwarding headers. The backend may
  // trust these for rate limiting in reverse-proxy deployments, so the web
  // proxy must make them authoritative.
  forwardedHeaders.set('x-forwarded-for', event.getClientAddress());
  forwardedHeaders.set('x-real-ip', event.getClientAddress());
  forwardedHeaders.set('x-forwarded-host', event.url.host);
  forwardedHeaders.set('x-forwarded-proto', event.url.protocol.replace(':', ''));

  // GET/HEAD must not carry a body. For all other methods we pass the
  // raw stream through; `duplex: 'half'` is required by the Node fetch
  // implementation when streaming a request body.
  const method = event.request.method.toUpperCase();
  const hasBody = method !== 'GET' && method !== 'HEAD';

  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetch(upstreamUrl, {
      method,
      headers: forwardedHeaders,
      body: hasBody ? event.request.body : undefined,
      // @ts-expect-error — Node 18+ fetch accepts `duplex` but the DOM
      // fetch typings don't include it yet.
      duplex: hasBody ? 'half' : undefined,
      redirect: 'manual',
    });
  } catch (err) {
    // Don't leak internal hostnames or stack traces; log server-side.
    console.error('[proxy] upstream fetch failed', {
      path: pathname,
      method,
      message: err instanceof Error ? err.message : String(err),
    });
    return new Response(JSON.stringify({ detail: 'Upstream API unreachable' }), {
      status: 502,
      headers: { 'content-type': 'application/json' },
    });
  }

  // Mirror the upstream response 1:1, except for hop-by-hop headers.
  const responseHeaders = stripHopByHop(upstreamResponse.headers);
  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: responseHeaders,
  });
};
