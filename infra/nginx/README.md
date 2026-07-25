# Nginx edge — canonical hosted config

Reference reverse-proxy config for the **Hosted** instance (`correlcore.com`),
per [ADR-0040](../../docs/adr/0040-selfhost-auth-edge-passthrough.md).

## Why this exists

Cookie-based login (ADR-0006) only works if the edge forwards `Set-Cookie`
untouched and keeps `/api` **same-origin** with the app. A hand-written server
block that gives auth endpoints their own `location` with different proxy params
silently drops the login cookie — the login then returns HTTP 200 but the
browser stores nothing, and the UI historically mislabelled this as
"E-Mail oder Passwort ist falsch". These files remove that trap.

## Contract (one-rule passthrough)

The edge does only three things:

1. Terminate TLS.
2. Reverse-proxy **all** paths to `correlcore-web` (the web container owns `/api`
   routing and `Set-Cookie`, ADR-0011).
3. Set `X-Forwarded-Proto: https`.

No per-path `/api` rule, no direct API routing, no `Set-Cookie` hiding/rewriting.

## Files

| File                                        | Install to                                            |
| ------------------------------------------- | ----------------------------------------------------- |
| `correlcore.com.conf`                       | `/etc/nginx/sites-available/` (symlink to `sites-enabled/`) |
| `snippets/correlcore-proxy-params.conf`     | `/etc/nginx/snippets/`                                 |

Both `location` blocks in `correlcore.com.conf` include the same snippet, so
auth and non-auth requests cannot diverge.

## Deploy

```bash
sudo cp infra/nginx/snippets/correlcore-proxy-params.conf /etc/nginx/snippets/
sudo cp infra/nginx/correlcore.com.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/correlcore.com.conf /etc/nginx/sites-enabled/
# adjust server_name / ssl_certificate* / upstream port first
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
you cannot include the snippet — but the same contract applies:

- Source `https://correlcore.com` → Destination `http://127.0.0.1:3010`
- Custom header **`X-Forwarded-Proto` = `https`** (required for Secure cookies)
- Proxy **all** paths (do not carve out `/api`)

Then run `verify-auth-cookie.sh` to confirm.

Related: [`hosted-nginx-edge.md`](../../docs/runbooks/hosted-nginx-edge.md) ·
[`hosted-topology-options.md`](../../docs/runbooks/hosted-topology-options.md)
