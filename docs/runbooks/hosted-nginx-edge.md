# Runbook — Hosted Nginx edge (`correlcore.com`)

Last updated: 2026-07-19  
**Milestone:** M10.2 Sprint 1  
**Plan:** [`../M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md`](../M10_2_PUBLIC_HOSTED_LAUNCH_PLAN.md)  
**Issue:** #460

Operator runbook for the **Hosted reference** instance. This is not a second
selfhost install guide — generic install stays in [`../selfhost/INSTALL.md`](../selfhost/INSTALL.md).

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

Adapt certificate paths to your ACME setup (certbot / Synology cert).

```nginx
# correlcore.com — Hosted edge (M10.2)
# Upstream = correlcore-web only (ADR-0011 proxies /api)

limit_req_zone $binary_remote_addr zone=correlcore_auth:10m rate=5r/s;

upstream correlcore_web {
    server 127.0.0.1:3010;  # WEB_HOST_PORT
    keepalive 16;
}

server {
    listen 80;
    listen [::]:80;
    server_name correlcore.com www.correlcore.com;
    return 301 https://correlcore.com$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name correlcore.com www.correlcore.com;

    # ssl_certificate     /path/to/fullchain.pem;
    # ssl_certificate_key /path/to/privkey.pem;

    # Security headers (parity with Traefik labels in production compose)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    client_max_body_size 2m;

    location /api/v1/auth/ {
        limit_req zone=correlcore_auth burst=20 nodelay;
        proxy_pass http://correlcore_web;
        include /etc/nginx/snippets/correlcore-proxy-params.conf;  # or inline below
    }

    location / {
        proxy_pass http://correlcore_web;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header Connection "";
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
}
```

If Synology **Application Portal → Reverse Proxy** is used instead of raw Nginx:

| Setting           | Value                                                           |
| ----------------- | --------------------------------------------------------------- |
| Source            | `https://correlcore.com:443`                                    |
| Destination       | `http://127.0.0.1:3010`                                         |
| WebSocket         | on if offered                                                   |
| **Custom header** | `X-Forwarded-Proto` = `https` (**required** for Secure cookies) |
| Custom header     | `X-Forwarded-For` / `X-Real-IP` as supported                    |

### B.2 Synology pitfalls

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

Cookie check: DevTools → after login attempt, `Set-Cookie` with `Secure` and `Https` site.

---

## D. Done when

- [ ] Web healthy on localhost
- [ ] Nginx/RP proxies to web with `X-Forwarded-Proto https`
- [ ] Traefik not on 80/443
- [ ] Hosted ENV set (`FRONTEND_BASE_URL` / `CORS_ORIGINS` / `COOKIE_SECURE`)
- [ ] Public DNS (or tunnel) reaches NAS edge
- [ ] Public smoke `/` + `/api/v1/health` green without VPN

SMTP / Mailpit removal → Sprint 2 (#461). Landing content polish → Sprint 3 (#462).
