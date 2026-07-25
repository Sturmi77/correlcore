# Nginx edge — canonical hosted config

Reference reverse-proxy config for the **Hosted** instance (`correlcore.com`),
per [ADR-0040](../../docs/adr/0040-selfhost-auth-edge-passthrough.md).

## Why this exists

Cookie-based login (ADR-0006) only works if the edge forwards `Set-Cookie`
untouched and keeps `/api` **same-origin** with the app. A hand-written server
block that gives auth endpoints their own `location` with different proxy params
silently drops the login cookie — the login then returns HTTP 200 but the
browser stores nothing, and the UI historically mislabelled this as
"E-Mail oder Passwort ist falsch". This file removes that trap.

> Note: for the July 2026 incident the actual strip was in the SvelteKit proxy
> (fixed in #527), not the edge. This config is defense-in-depth **and** the
> deployable reference — an edge that violates the contract below reproduces the
> same symptom regardless of the app code.

## Contract (one-rule passthrough)

The edge does only three things:

1. Terminate TLS.
2. Reverse-proxy **all** paths to `correlcore-web` (the web container owns `/api`
   routing and `Set-Cookie`, ADR-0011).
3. Set `X-Forwarded-Proto: https`.

No per-path `/api` rule, no direct API routing, no `Set-Cookie` hiding/rewriting.

## Self-contained — no snippet file

`correlcore.com.conf` is a **single file with no `include`**. The proxy params
are defined once at the `server{}` level; both `location` blocks inherit them
automatically because neither declares its own `proxy_set_header`. This is what
keeps auth and non-auth requests identical **and** makes the config deployable on
a standalone reverse-proxy machine (or pasted into a Synology custom config)
where you cannot drop extra files into `/etc/nginx/snippets/`.

> ⚠️ Do **not** add a `proxy_set_header` inside a `location` block — nginx then
> stops inheriting the server-level ones for that location, which reintroduces
> the bug.

## Remote edge (Nginx on a different machine than the app)

Point the upstream at the **app host** as reachable from the edge machine — not
`127.0.0.1`:

```nginx
upstream correlcore_web {
    server apphost.tailnet-abcd.ts.net:3010;   # APP_HOST:WEB_PORT — trusted link only
    keepalive 16;
}
```

The web container must listen on an interface reachable from the edge machine
(not bound to loopback on the app host).

> ⚠️ **Encrypt the edge→app hop.** TLS terminates at the edge, so
> `proxy_pass http://…` sends login credentials, **session cookies**, and
> private API data to the app host in **plaintext**. Only run a remote edge when
> that hop is itself encrypted/trusted — a **Tailscale/WireGuard tailnet**, a
> VPN, or a private point-to-point segment. **Do not** cross an untrusted or
> shared LAN/WAN with a plain `http://` upstream. If the link cannot be trusted,
> terminate TLS on the app host as well and use an HTTPS upstream:
> `proxy_pass https://correlcore_web;` with `proxy_ssl_verify on;` and the
> matching `proxy_ssl_*` / `proxy_ssl_name` directives. A same-host edge
> (`127.0.0.1`) is unaffected — the hop never leaves the box.

## Deploy

Copy `correlcore.com.conf` to the edge (adjust `server_name`,
`ssl_certificate*`, and the upstream target first):

```bash
# on the edge machine
sudo cp correlcore.com.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/correlcore.com.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Then **verify the auth cookie actually survives the edge**:

```bash
BASE_URL=https://correlcore.com scripts/verify-auth-cookie.sh
```

A green run means login persists the session. A red run tells you which hop
breaks (see the script output and ADR-0040).

## Synology Reverse Proxy variant

If you use Synology **Application Portal → Reverse Proxy** instead of raw Nginx,
the same contract applies:

- Source `https://correlcore.com` → Destination the web container (host:port)
- Custom header **`X-Forwarded-Proto` = `https`** (required for Secure cookies)
- Proxy **all** paths (do not carve out `/api`)

Then run `verify-auth-cookie.sh` to confirm.

Related: [`hosted-nginx-edge.md`](../../docs/runbooks/hosted-nginx-edge.md) ·
[`hosted-topology-options.md`](../../docs/runbooks/hosted-topology-options.md)
