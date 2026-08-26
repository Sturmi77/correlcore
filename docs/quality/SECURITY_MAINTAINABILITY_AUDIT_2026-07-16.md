# Security & Maintainability Audit — 2026-07-16

Living audit of CorrelCore (`main` @ post-v1.0). Complements
[`M9_PENTEST.md`](M9_PENTEST.md) and older frontend audits under
`docs/frontend/`.

**Scope:** auth/crypto, secrets hygiene, rate limits, abuse resistance,
documentation accuracy, maintainability.

**Verdict:** No critical auth bypass or committed production credentials.
Design is strong (HttpOnly cookies, DEK wrapping, RLS, SlowAPI on sensitive
routes). Highest residual risks were refresh-token race, production config
gaps, and deploy/bootstrap drift — several remediations shipped with this
audit (see § Remediated).

---

## Scorecard

| Area            | Grade | Notes                                                                  |
| --------------- | ----- | ---------------------------------------------------------------------- |
| Auth & sessions | B+    | Solid cookie/JWT model; atomic refresh rotate now fixed                |
| Crypto at rest  | A-    | Per-user DEK + MultiFernet; Fernet validity checked in staging/prod    |
| Secrets hygiene | B+    | No real secrets in git; gitleaks allowlist tightened                   |
| Rate limits     | B     | Auth/entries covered; export/refresh/logout/delete now limited         |
| Authorization   | A-    | App filters + Postgres RLS; admin decrypt path is intentional          |
| Docs accuracy   | B-    | v1.0 messaging + React GUI docs corrected; sprint archives still noisy |
| Maintainability | B-    | Five compose/env stacks; no Dependabot; React GUI still uns scaffolded |

---

## Findings

Severity: **Critical** / **High** / **Medium** / **Low** / **Info**.
Status: **Fixed** (this PR) / **Open** / **Accepted**.

### High

| ID  | Status | Finding                                                                                          | Location                                              |
| --- | ------ | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| H1  | Fixed  | Refresh rotation was TOCTOU (`is_valid` then `rotate`); concurrent refresh could mint 2 sessions | `redis_client.py`, `auth_service.py`                  |
| H2  | Fixed  | `DEV_VIEW_ENABLED` / `DEBUG` not rejected in production                                          | `config.py`                                           |
| H3  | Fixed  | Gitleaks path-allowlisted entire `ci-api.yml` (stale regex)                                      | `.gitleaks.toml`                                      |
| H4  | Fixed  | `SLUG_HMAC_KEY` missing from most env examples + bootstrap                                       | `infra/**/.env*.example`, `bootstrap-selfhost-env.sh` |

### Medium

| ID  | Status | Finding                                                                   | Location                             |
| --- | ------ | ------------------------------------------------------------------------- | ------------------------------------ |
| M1  | Fixed  | `clear_auth_cookies` omitted Secure/SameSite/HttpOnly                     | `auth_cookies.py`                    |
| M2  | Fixed  | Production secret checks skipped Fernet validity, MinIO default, CORS `*` | `config.py`                          |
| M3  | Fixed  | `/auth/refresh`, `/auth/logout` unrate-limited                            | `auth.py`                            |
| M4  | Fixed  | Export + account-delete unrate-limited                                    | `export.py`, `user.py`               |
| M5  | Fixed  | Photo upload buffered entire body before size check                       | `media.py`                           |
| M6  | Fixed  | `TokenStore.revoke_all` used Redis `KEYS`                                 | `redis_client.py`                    |
| M7  | Open   | Access JWT still returned in JSON body (XSS can steal despite HttpOnly)   | `auth.py` TokenResponse              |
| M8  | Open   | Password policy min 8 + letter/digit — thin for Art. 9 data               | `schemas/auth.py`                    |
| M9  | Open   | SlowAPI fails hard when Redis is down (no in-memory fallback)             | `rate_limit.py`                      |
| M10 | Open   | Five near-duplicate compose/env stacks drift                              | `infra/docker`, `dockhand`, `dockge` |
| M11 | Open   | No Dependabot/Renovate despite M9 note                                    | `.github/`                           |
| M12 | Fixed  | Content-Type CSRF gate now enforced (415 on non-JSON mutating bodies)     | `core/csrf.py`, `main.py`            |

### Low / Info

| ID  | Status   | Finding                                                                |
| --- | -------- | ---------------------------------------------------------------------- |
| L1  | Accepted | Access tokens not denylisted on logout (≤15 min TTL residual; ADR-0006) |
| L2  | Open     | bcrypt 72-byte silent truncation                                       |
| L3  | Accepted | `python-jose` + `ecdsa` advisory (HS256-only; tracked in M9_PENTEST)   |
| L4  | Open     | Tag `color` not regex-validated (`#RRGGBB`) — CSS injection surface    |
| L5  | Open     | Login password field unbounded length (CPU cost on bcrypt)             |
| L6  | Fixed    | README “pre-alpha” / CONTRIBUTING “until v1.0” contradicted v1.0 badge |
| L7  | Fixed    | AGENTS.md / CLAUDE.md advertised missing `pnpm dev:react`              |
| I1  | Info     | External pentest still pending (`M9_PENTEST.md`)                       |
| I2  | Info     | Frontend Vitest has no coverage floor; backend floor is 70%            |

---

## What’s done well

- HttpOnly + SameSite=strict cookies; refresh cookie path-scoped to `/api/v1/auth/refresh`
- Refresh reuse → revoke-all (now atomic)
- bcrypt-12 + dummy hash on failed login; enumeration-safe register/forgot
- Per-user DEK, request-scoped ContextVar, no key logging
- Dual authz: service `user_id` filters + Postgres RLS
- SlowAPI on auth-sensitive and most data routes; proxy header trust off by default
- Security CI: gitleaks (full history), pip-audit, pnpm audit
- No `{@html}` / `dangerouslySetInnerHTML` sinks found
- Open redirect hardening via `safeNext` on login

---

## Remediated in this change set

1. Atomic Lua refresh rotate + SCAN-based `revoke_all`
2. Production guards: `DEBUG`, `DEV_VIEW_ENABLED`, valid Fernet keys, MinIO secret, CORS allowlist
3. Cookie clear attributes match set attributes
4. Rate limits: refresh 30/min, logout 20/min, exports 10/hour, delete 5/min
5. Chunked photo upload with early 413
6. Gitleaks allowlist narrowed to CI Fernet fixture string
7. `SLUG_HMAC_KEY` in bootstrap + all selfhost env examples
8. Docs: v1.0 messaging, React GUI “planned not scaffolded”

---

## Remediated 2026-08-26 (#779)

- **M12 — Content-Type CSRF gate.** `ContentTypeCSRFMiddleware` rejects
  state-changing requests with a non-JSON body (415); `multipart/form-data`
  allowed for media uploads, bodiless mutations allowed. Tests in
  `tests/test_csrf_content_type.py`. ADR-0006 amended.
- **S3 — CSP report-only.** Report-only `Content-Security-Policy-Report-Only`
  added to the Traefik `security-headers` middleware
  (`infra/docker/docker-compose.yml`); observe first, then promote to a blocking
  header once the report window is clean and `style-src 'unsafe-inline'` is
  removed. ADR-0006 amended.
- **L1 — access-token denylist.** Accepted residual (≤15 min TTL on an
  HttpOnly + SameSite=strict cookie); documented in ADR-0006. Revisit when the
  Redis job queue (#761) lands.
- **MFA / lockout.** Explicit defer decision recorded in ADR-0004 (TOTP-MFA
  moved post-launch; per-account lockout accepted residual behind SlowAPI).

---

## Recommended follow-ups (not in this PR)

1. Omit `access_token` from browser cookie flows (M7)
2. Strengthen password policy / breached-password check (M8)
3. Define Redis-outage policy for SlowAPI (M9)
4. Add Dependabot for uv + pnpm (M11)
5. Collapse compose/env stacks to one generated source of truth (M10)
6. Schedule external pentest (I1)
7. Archive or stamp historical `docs/quality/*` / `docs/frontend/*AUDIT*` so open findings are not confused with live backlog

---

## Test plan

- `cd backend && uv run --python 3.12 pytest tests/test_auth_service.py tests/test_auth_cookies.py tests/test_settings_cookie_secure.py tests/test_settings_production_guards.py tests/test_media.py -q`
- `uv run --python 3.12 ruff check app tests`
- Confirm staging/quickstart still starts after setting `SLUG_HMAC_KEY`
