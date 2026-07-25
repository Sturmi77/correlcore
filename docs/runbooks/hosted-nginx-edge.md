# Runbook — Hosted Nginx edge (`correlcore.com`)

Last updated: 2026-07-19  
**Milestone:** M10.2 Sprint 1  
**Plan:** [`../M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md`](../M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md)  
**Issue:** #460  
**Auth-edge contract:** [ADR-0040](../adr/0040-selfhost-auth-edge-passthrough.md) — one-rule passthrough; the canonical config is shipped at [`infra/nginx/`](../../infra/nginx/), not hand-written.  
**Combined cutover (with SMTP):** [`hosted-cutover.md`](hosted-cutover.md)

Operator runbook for the **Hosted reference** instance. This is not a second
selfhost install guide — generic install stays in [`../selfhost/INSTALL.md`](../selfhost/INSTALL.md).
Prefer the combined cutover when going public so verify-mail works in the same window.

## Goals

1. Terminate TLS on **host Nginx** (or Synology Reverse Proxy / Web Station in front of Nginx).
2. Proxy **all** paths to `correlcore-web` on localhost (ADR-0011 handles `/api/*`).
3. Set Hosted app ENV for `https://correlcore.com`.
4. Keep **Compose Traefik off** ports 80/443 (no dual edge).
5. End users reach the app **without VPN/Tailscale**.

## Current DNS snapshot (repo Sprint 1)

Observed 2026-07-19 from CI/agent network (re-check before cutover):

| Record             | Value                                   | Notes                                                                          |
| ------------------ | --------------------------------------- | ------------------------------------------------------------------------------ |
| `correlcore.com` A | `217.160.0.166`                         | IONOS; HTTP answers **Apache** (website builder / placeholder), not CorrelCore |
| AAAA               | present                                 | IONOS                                                                          |
| MX                 | `mx00/mx01.ionos.de`                    | Useful for Sprint 2 / `security@`                                              |
| SPF TXT            | `v=spf1 include:_spf-eu.ionos.com ~all` | Extend in Sprint 2 if SMTP relay ≠ IONOS                                       |

**Implication:** Sprint 1 cutover is not “enable Nginx only” — DNS (or an IONOS
reverse proxy) must eventually send public traffic to the NAS edge. Until then,
repo deliverables below are ready; live smoke against CorrelCore remains blocked.

## Architecture (target)

```text
Internet → DNS correlcore.com → Host Nginx :443
         → proxy_pass http://127.0.0.1:${WEB_HOST_PORT}
         → correlcore-web → INTERNAL_API_URL → correlcore-api
```

One TLS edge. Tailscale optional for **admin** only.

---

## A. App stack on NAS (before opening WAN)

### A.1 Bind web to localhost

Dockhand / quickstart: set host bind so web is not required on LAN/WAN:

```env
# Example — exact variable names follow your compose variant
WEB_HOST_PORT=3010
# Prefer binding 127.0.0.1:3010 (Dockhand TAILSCALE_IP=127.0.0.1 or equivalent)
```

Confirm: only Nginx (or Synology RP) needs WAN; web listens on loopback.

### A.2 Traefik off

If using [`infra/docker/docker-compose.yml`](../../infra/docker/docker-compose.yml):
do **not** publish Traefik `80/443` on the Hosted NAS while Nginx owns those ports.
Prefer quickstart/Dockhand **without** Traefik for Hosted-Nginx mode.

### A.3 Hosted ENV (minimum)

```env
APP_ENV=production
DOMAIN=correlcore.com
FRONTEND_BASE_URL=https://correlcore.com
CORS_ORIGINS=https://correlcore.com
COOKIE_SECURE=true
# SECRET_KEY, ENCRYPTION_KEY, SLUG_HMAC_KEY, DB/Redis — production-strong, offline backup
# SMTP_* — Sprint 2 (#461); Mailpit OK until then
```

Restart `api` + `web` (+ `worker`) after ENV change.

### A.4 Local smoke (on NAS)

```bash
curl -sf "http://127.0.0.1:${WEB_HOST_PORT}/" | head -c 200
curl -sf "http://127.0.0.1:${WEB_HOST_PORT}/api/v1/health"
```

---

## B. Nginx (or Synology Reverse Proxy)

### B.1 Canonical Nginx server block

**Do not hand-write this** — copy the shipped, tested config
([ADR-0040](../adr/0040-selfhost-auth-edge-passthrough.md)). It is a **single
self-contained file, no `include` snippet**, so it also works on a standalone
edge machine or a Synology custom config:

```bash
# 1) Get the file onto the edge machine first (it lives at infra/nginx/ in the
#    repo, which the edge box usually does not have). From a repo checkout:
scp infra/nginx/correlcore.com.conf <edge-host>:/tmp/correlcore.com.conf
# 2) On the edge machine — adjust server_name / ssl_certificate* / upstream first:
sudo install -m 0644 /tmp/correlcore.com.conf /etc/nginx/sites-available/correlcore.com.conf
sudo ln -sf /etc/nginx/sites-available/correlcore.com.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

See [`infra/nginx/README.md`](../../infra/nginx/README.md) for the full file and
deploy notes (incl. the remote-edge upstream). The key property (ADR-0040): the
proxy params are defined **once at `server{}` level** and both `location /` and
`location /api/v1/auth/` inherit them (neither declares its own
`proxy_set_header`), so auth requests can never be proxied differently from the
rest of the app. A separate auth `location` with its own (or missing) proxy
params is precisely what drops the login `Set-Cookie` and makes a correct login
read as "E-Mail oder Passwort ist falsch".

After reload, **verify the cookie actually survives the edge**:

```bash
BASE_URL=https://correlcore.com scripts/verify-auth-cookie.sh
```

If Synology **Application Portal → Reverse Proxy** is used instead of raw Nginx:

| Setting           | Value                                                           |
| ----------------- | --------------------------------------------------------------- |
| Source            | `https://correlcore.com:443`                                    |
| Destination       | `http://127.0.0.1:3010`                                         |
| WebSocket         | on if offered                                                   |
| **Custom header** | `X-Forwarded-Proto` = `https` (**required** for Secure cookies) |
| Custom header     | `X-Forwarded-For` / `X-Real-IP` as supported                    |

### B.2 Pitfalls (Nginx / Synology / NPM)

- **`502 Bad Gateway` with `upstream sent too big header`** → the SvelteKit web
  container sends large response headers (adapter-node `Link: rel=preload`), and
  the reverse proxy's default `proxy_buffer_size` (4k/8k) is too small. The
  forward target is reachable and the config otherwise correct — it is purely a
  buffer size problem. **Raise the header buffer on every edge:**

  ```nginx
  proxy_buffer_size       32k;
  proxy_buffers           8 32k;
  proxy_busy_buffers_size 64k;
  ```

  The shipped `infra/nginx/correlcore.com.conf` already has this. On **Nginx
  Proxy Manager (NPM)** paste exactly these three lines into the Proxy Host →
  **Advanced** field (server-context directives — no `location`/`server` block).
  Diagnose via the host error log: `tail /data/logs/proxy-host-*_error.log`.
- **Separate auth `location` that omits the shared proxy params** → login returns
  200 but no `Set-Cookie` reaches the browser → the UI shows
  "E-Mail oder Passwort ist falsch" although the password was correct. Fix
  (ADR-0040): define the proxy params once at `server{}` level and let both
  locations inherit them — do **not** put a `proxy_set_header` inside a location
  (that stops inheritance for it). Confirm with `scripts/verify-auth-cookie.sh`.
- **Never** add `proxy_hide_header Set-Cookie;` or `proxy_cookie_path ...;` on
  the auth/`/` locations — both strip or rewrite the session cookie.
- Missing `X-Forwarded-Proto https` → browser drops `Secure` cookies → login “does nothing”.
- Web Station + Reverse Proxy double-proxy can rewrite headers — prefer one hop to web.
- Do not enable Compose Traefik on the same 80/443.
- Userspace Tailscale: keep admin via Tailscale; do not require it for public users.

### B.3 Router

Forward WAN **80** and **443** to the NAS Nginx/RP host. Verify from mobile data (not LAN/Tailscale).

### B.4 DNS cutover options

| Option                                          | When                               | Action                                                                 |
| ----------------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------- |
| **A — Point apex at NAS**                       | Public IPv4/IPv6 on home, no CGNAT | Change A/AAAA from IONOS web IP to NAS public IP; keep MX/SPF for mail |
| **B — IONOS (or other) reverse proxy / tunnel** | CGNAT or want to hide home IP      | Keep DNS on IONOS; proxy/tunnel to NAS; still one logical edge         |
| **C — Defer public cutover**                    | Landing still on IONOS builder     | Finish Nginx+ENV on NAS; cut DNS when ready (Sprint 1 remaining)       |

Do **not** run IONOS Apache and NAS Nginx both as public apex without a clear redirect story.

---

## C. Public smoke (after DNS/edge cutover)

```bash
curl -sfI "https://correlcore.com/" | head -20
# Expect: HTTP/2 200, HSTS, app HTML (not IONOS placeholder)

curl -sf "https://correlcore.com/api/v1/health"
# Expect: JSON health payload

# From mobile data / non-home network:
# open https://correlcore.com/ and /auth/login — no VPN
```

Cookie check (authoritative — do not skip):

```bash
BASE_URL=https://correlcore.com scripts/verify-auth-cookie.sh
# PASS = login 200 + Set-Cookie present + /auth/me 200
```

Manual equivalent: DevTools → after login, the `POST /api/v1/auth/login` response
carries `Set-Cookie` and the cookie appears under Storage/Application for the
site. A 200 login with **no** stored cookie is the ADR-0040 edge-strip bug.

---

## D. Done when

- [ ] Web healthy on localhost
- [ ] Nginx/RP proxies to web with `X-Forwarded-Proto https`
- [ ] Traefik not on 80/443
- [ ] Hosted ENV set (`FRONTEND_BASE_URL` / `CORS_ORIGINS` / `COOKIE_SECURE`)
- [ ] Public DNS (or tunnel) reaches NAS edge
- [ ] Public smoke `/` + `/api/v1/health` green without VPN
- [ ] `scripts/verify-auth-cookie.sh` returns **PASS** (login cookie survives the edge, ADR-0040)

SMTP / Mailpit removal → Sprint 2 (#461). Landing content polish → Sprint 3 (#462).
