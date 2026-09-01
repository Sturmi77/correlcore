# Security & Maintainability Audit — 2026-07-16

Living audit of CorrelCore. Complements [`M9_PENTEST.md`](M9_PENTEST.md)
and older frontend audits under `docs/frontend/`.

**Last refresh:** 2026-08-25 (`main` @ v1.3) — gap analysis vs Art. 9 SaaS
baseline. Tracking epic:
[#776](https://github.com/Sturmi77/correlcore/issues/776).

**Update 2026-08-28:** three tracked follow-ups landed — **Q1** (analytics
monolith) split in [#787](https://github.com/Sturmi77/correlcore/issues/787),
**M12** (Content-Type CSRF) enforced and **S3** (report-only CSP) partially
addressed in [#789](https://github.com/Sturmi77/correlcore/issues/789), which
also records the **L1** (access-token denylist) and **MFA/lockout** ADR
decisions. Rows and the follow-up table below reflect this; issues #777 and
#779 are closed. Remaining hardening (S3 report sink, CSRF exception scoping,
JWT TTL cap) is tracked in
[#791](https://github.com/Sturmi77/correlcore/issues/791).

**Scope:** auth/crypto, secrets hygiene, rate limits, abuse resistance,
documentation accuracy, code quality gates, maintainability.

**Verdict (2026-08-25):** No critical auth bypass or committed production
credentials. Design remains strong (HttpOnly cookies, DEK wrapping, RLS,
SlowAPI, security CI). Jul-2026 remediations held; six former Open Medium/Low
items are now **Fixed**. Highest residual risk shifted from config races to
**scale debt** (analytics monolith + hand-maintained FE/BE types) and
**missing external assurance** (pentest, DAST). _[2026-08-28: the
analytics monolith (Q1) has since been split —
[#787](https://github.com/Sturmi77/correlcore/issues/787); scale debt now
centres on the hand-maintained FE/BE types.]_ _[2026-09-01: SAST via CodeQL
landed — [#801](https://github.com/Sturmi77/correlcore/issues/801); external
assurance now centres on the pending pentest and DAST.]_

---

## Scorecard

| Area                       | Grade (2026-08-25) | Jul 2026 | Notes                                                                              |
| -------------------------- | ------------------ | -------- | ---------------------------------------------------------------------------------- |
| Auth & sessions            | A-                 | B+       | Cookie/JWT model solid; body JWT opt-in; atomic refresh rotate                     |
| Crypto at rest             | A-                 | A-       | Per-user DEK + MultiFernet; Fernet validity checked in staging/prod                |
| Secrets hygiene            | A-                 | B+       | No real secrets in git; gitleaks + Dependabot                                      |
| Rate limits                | A-                 | B        | Auth/data/export/delete covered; Redis blip → in-memory fallback                   |
| Authorization              | A-                 | A-       | App filters + Postgres RLS                                                         |
| Supply chain / CI security | B+                 | B        | gitleaks, pip-audit, pnpm audit, Dependabot, CodeQL SAST; DAST/Trivy still pending |
| Code quality gates         | A-                 | B+       | ruff, mypy strict, pytest cov≥70, ESLint, style/contrast gates                     |
| Docs accuracy              | B                  | B-       | React GUI correctly “planned”; sprint archives still noisy                         |
| Maintainability            | B-                 | B-       | Compose drift + god modules + hand DTOs; React still unscaffolded                  |
| External assurance         | C+                 | C+       | External pentest still pending (`M9_PENTEST.md`)                                   |

---

## Findings

Severity: **Critical** / **High** / **Medium** / **Low** / **Info**.  
Status: **Fixed** / **Open** / **Accepted**.

Issue links point at the 2026-08-25 follow-up epic and children.

### High (original Jul set — all Fixed)

| ID  | Status | Finding                                                                                          | Location                                              |
| --- | ------ | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| H1  | Fixed  | Refresh rotation was TOCTOU (`is_valid` then `rotate`); concurrent refresh could mint 2 sessions | `redis_client.py`, `auth_service.py`                  |
| H2  | Fixed  | `DEV_VIEW_ENABLED` / `DEBUG` not rejected in production                                          | `config.py`                                           |
| H3  | Fixed  | Gitleaks path-allowlisted entire `ci-api.yml` (stale regex)                                      | `.gitleaks.toml`                                      |
| H4  | Fixed  | `SLUG_HMAC_KEY` missing from most env examples + bootstrap                                       | `infra/**/.env*.example`, `bootstrap-selfhost-env.sh` |

### Medium

| ID  | Status | Finding                                                                   | Location                             | Track                                                                            |
| --- | ------ | ------------------------------------------------------------------------- | ------------------------------------ | -------------------------------------------------------------------------------- |
| M1  | Fixed  | `clear_auth_cookies` omitted Secure/SameSite/HttpOnly                     | `auth_cookies.py`                    | —                                                                                |
| M2  | Fixed  | Production secret checks skipped Fernet validity, MinIO default, CORS `*` | `config.py`                          | —                                                                                |
| M3  | Fixed  | `/auth/refresh`, `/auth/logout` unrate-limited                            | `auth.py`                            | —                                                                                |
| M4  | Fixed  | Export + account-delete unrate-limited                                    | `export.py`, `user.py`               | —                                                                                |
| M5  | Fixed  | Photo upload buffered entire body before size check                       | `media.py`                           | —                                                                                |
| M6  | Fixed  | `TokenStore.revoke_all` used Redis `KEYS`                                 | `redis_client.py`                    | —                                                                                |
| M7  | Fixed  | Access JWT in JSON body by default (XSS steal despite HttpOnly)           | `auth.py`                            | Opt-in `?include_access_token=true` only; cookie refresh never returns body JWTs |
| M8  | Fixed  | Password policy min 8 + letter/digit — thin for Art. 9 data               | `password_policy.py`                 | Min **12** + letter/digit + common-password denylist                             |
| M9  | Fixed  | SlowAPI fails hard when Redis is down (no in-memory fallback)             | `rate_limit.py`                      | `in_memory_fallback_enabled=True`                                                |
| M10 | Open   | Near-duplicate compose/env stacks drift                                   | `infra/docker`, `dockhand`, `dockge` | [#781](https://github.com/Sturmi77/correlcore/issues/781) (D-I1)                 |
| M11 | Fixed  | No Dependabot/Renovate despite M9 note                                    | `.github/dependabot.yml`             | npm, pip/backend, github-actions                                                 |
| M12 | Fixed  | Content-Type CSRF gate enforced (415 on non-JSON mutating bodies)         | `core/csrf.py`, `main.py`            | [#789](https://github.com/Sturmi77/correlcore/issues/789) (M12)                  |

### Low / Info

| ID  | Status   | Finding                                                                                                     | Track                                                                       |
| --- | -------- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| L1  | Accepted | Access tokens not denylisted on logout (15-min default TTL residual; setting unbounded, see #791; ADR-0006) | [#789](https://github.com/Sturmi77/correlcore/issues/789) accepted residual |
| L2  | Open     | bcrypt 72-byte silent truncation                                                                            | Documented; accept or migrate hasher later                                  |
| L3  | Accepted | `python-jose` + `ecdsa` advisory (HS256-only; M9_PENTEST)                                                   | —                                                                           |
| L4  | Fixed    | Tag `color` not regex-validated (`#RRGGBB`)                                                                 | `schemas/tag.py` hex validator                                              |
| L5  | Fixed    | Login password field unbounded length                                                                       | `max_length=128` on login                                                   |
| L6  | Fixed    | README / CONTRIBUTING contradicted v1.0 badge                                                               | —                                                                           |
| L7  | Fixed    | AGENTS.md advertised missing `pnpm dev:react`                                                               | Correctly “planned, not scaffolded”                                         |
| I1  | Open     | External pentest still pending (`M9_PENTEST.md`)                                                            | [#782](https://github.com/Sturmi77/correlcore/issues/782)                   |
| I2  | Open     | Frontend Vitest has no coverage floor; backend floor is 70%                                                 | [#780](https://github.com/Sturmi77/correlcore/issues/780)                   |

### Added 2026-08-25 (gap analysis)

| ID  | Sev    | Status   | Finding                                                                                                             | Location                    | Track                                                                                                                          |
| --- | ------ | -------- | ------------------------------------------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| S1  | Medium | Partial  | SAST via CodeQL now in CI (`codeql.yml`, python + js/ts, security-extended); DAST + container image scan still open | `.github/workflows/`        | [#776](https://github.com/Sturmi77/correlcore/issues/776) (P2 checklist)                                                       |
| S2  | Medium | Accepted | MFA / account lockout deferred (ADR-0004 records the decision)                                                      | ADR-0004                    | [#789](https://github.com/Sturmi77/correlcore/issues/789) (defer decision)                                                     |
| S3  | Medium | Partial  | Report-only CSP shipped (prod compose); no report sink / not enforcing yet                                          | `docker-compose.yml`        | [#789](https://github.com/Sturmi77/correlcore/issues/789), hardening [#791](https://github.com/Sturmi77/correlcore/issues/791) |
| Q1  | High   | Fixed    | `insight_engine.py` split into `app.services.insights.*` family modules                                             | `services/insights/`        | [#787](https://github.com/Sturmi77/correlcore/issues/787)                                                                      |
| Q2  | High   | Open     | Hand-maintained FE DTOs; enum/range contract tests only (no OpenAPI→TS)                                             | `apps/web/src/lib/api/`     | [#778](https://github.com/Sturmi77/correlcore/issues/778)                                                                      |
| Q3  | Medium | Open     | Oversized Svelte routes (settings ~1.3k, insights ~1.1k, trends ~0.6k)                                              | `apps/web/src/routes/`      | [#776](https://github.com/Sturmi77/correlcore/issues/776) (P1 checklist)                                                       |
| Q4  | Medium | Open     | CI e2e is mocked smoke only                                                                                         | `ci-web.yml`                | [#780](https://github.com/Sturmi77/correlcore/issues/780)                                                                      |
| Q5  | Medium | Open     | Path-filtered CI can skip cross-stack contract tests                                                                | `ci-api.yml` / `ci-web.yml` | [#780](https://github.com/Sturmi77/correlcore/issues/780)                                                                      |
| Q6  | Low    | Open     | OpenAPI app version string still `0.0.1` while package is 1.3.0                                                     | `main.py`                   | [#776](https://github.com/Sturmi77/correlcore/issues/776) docs hygiene                                                         |
| Q7  | Low    | Open     | `packages/` empty; dual PII scrub lists FE/BE can drift                                                             | scrubbers                   | Soft-coupled to [#778](https://github.com/Sturmi77/correlcore/issues/778)                                                      |
| Q8  | Low    | Open     | ADR-0007 still implies workers/health TBD; workers exist                                                            | ADR-0007                    | [#776](https://github.com/Sturmi77/correlcore/issues/776) docs hygiene                                                         |

---

## What’s done well

- HttpOnly + SameSite=strict cookies; refresh cookie path-scoped to `/api/v1/auth/refresh`
- Refresh reuse → revoke-all (atomic Lua rotate)
- bcrypt-12 + dummy hash on failed login; enumeration-safe register/forgot
- Password policy min 12 + denylist; login password length capped
- Per-user DEK, request-scoped ContextVar, no key logging
- Dual authz: service `user_id` filters + Postgres RLS
- SlowAPI on auth-sensitive and most data routes; in-memory fallback on Redis blip; proxy header trust opt-in
- Security CI: gitleaks (full history), pip-audit, pnpm audit `--prod`, Dependabot
- Body access JWT omitted on cookie flows (Capacitor/API opt-in only)
- Tag color hex validation; media chunked upload + EXIF strip
- No `{@html}` / `dangerouslySetInnerHTML` sinks found under `apps/web/src`
- Open redirect hardening via `safeNext` on login
- PII/SHD scrubbing for structured logs and GlitchTip/Sentry
- Quality gates: ruff, mypy strict, pytest cov≥70%, ESLint, svelte-check, contrast/style/token guards

---

## Remediated in original 2026-07-16 change set

1. Atomic Lua refresh rotate + SCAN-based `revoke_all`
2. Production guards: `DEBUG`, `DEV_VIEW_ENABLED`, valid Fernet keys, MinIO secret, CORS allowlist
3. Cookie clear attributes match set attributes
4. Rate limits: refresh 30/min, logout 20/min, exports 10/hour, delete 5/min
5. Chunked photo upload with early 413
6. Gitleaks allowlist narrowed to CI Fernet fixture string
7. `SLUG_HMAC_KEY` in bootstrap + all selfhost env examples
8. Docs: v1.0 messaging, React GUI “planned not scaffolded”

## Remediated after Jul 2026 (confirmed 2026-08-25)

1. **M7** — Omit body JWT on browser cookie flows; opt-in `?include_access_token=true`
2. **M8** — Password min 12 + strength validator + denylist (`password_policy.py`)
3. **M9** — `in_memory_fallback_enabled=True` for SlowAPI
4. **M11** — `.github/dependabot.yml` (npm, pip/backend, actions)
5. **L4** — Tag `color` hex `#RRGGBB` validator
6. **L5** — Login password `max_length=128`

## Remediated 2026-08-28 (#787, #789)

1. **Q1** — `insight_engine.py` split into an `app.services.insights.*` package
   (correlation / weekday / multivariate / symptoms / changepoint / shared),
   with `insight_engine` kept as the thin orchestrator + re-export facade
   ([#787](https://github.com/Sturmi77/correlcore/issues/787)).
2. **M12** — `ContentTypeCSRFMiddleware` rejects non-JSON mutating bodies with
   415 (`multipart/form-data` allowed for media uploads); registered inside
   CORS and RequestID so a 415 still carries CORS + `X-Request-ID`
   ([#789](https://github.com/Sturmi77/correlcore/issues/789)).
3. **S3** — report-only `Content-Security-Policy-Report-Only` on the Traefik
   `security-headers` middleware (observe before enforce). Status **Partial**:
   no report sink yet and prod-compose only — report destination + non-prod
   rollout tracked in
   [#789](https://github.com/Sturmi77/correlcore/issues/789) /
   [#791](https://github.com/Sturmi77/correlcore/issues/791).
4. **L1 / MFA** — decisions recorded: access-token denylist accepted as a
   ≤15-min residual (ADR-0006); TOTP-MFA deferred post-launch, per-account
   lockout accepted behind SlowAPI (ADR-0004).

**Follow-up hardening (review-bot notes, not blocking — tracked in
[#791](https://github.com/Sturmi77/correlcore/issues/791)):** scope the
multipart CSRF exception to the upload path, reject body-present requests with
an empty `Content-Type`, give the report-only CSP a `report-uri`/`report-to`
plus roll it to the non-prod compose stacks, and bound
`JWT_ACCESS_TOKEN_EXPIRE_MINUTES` for the ADR-0006 ≤15-min residual.

---

## Recommended follow-ups (tracked)

Epic: [#776](https://github.com/Sturmi77/correlcore/issues/776)

| Priority | Action                                                                                                                                                              | Issue                                                               |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| ~~P0~~   | ✅ Split `insight_engine.py` / bound analytics modules — **done**                                                                                                   | [#777](https://github.com/Sturmi77/correlcore/issues/777) (#787)    |
| P0       | OpenAPI → TS types / `packages/api-types` + widen contract CI                                                                                                       | [#778](https://github.com/Sturmi77/correlcore/issues/778)           |
| P1       | Decompose insights / settings / trends pages                                                                                                                        | [#776](https://github.com/Sturmi77/correlcore/issues/776) checklist |
| P1       | Vitest coverage thresholds + real-API e2e + contract path filters                                                                                                   | [#780](https://github.com/Sturmi77/correlcore/issues/780)           |
| P1       | Compose single-source generation (D-I1 / M10)                                                                                                                       | [#781](https://github.com/Sturmi77/correlcore/issues/781)           |
| ~~P1~~   | ✅ Content-Type CSRF (M12) + CSP / denylist / MFA decisions — **done**                                                                                              | [#779](https://github.com/Sturmi77/correlcore/issues/779) (#789)    |
| P2       | CodeQL SAST done ([#801](https://github.com/Sturmi77/correlcore/issues/801)); remaining: optional Trivy image scan + DAST; docs hygiene (ADR-0007, OpenAPI version) | [#776](https://github.com/Sturmi77/correlcore/issues/776) checklist |
| P3       | External pentest                                                                                                                                                    | [#782](https://github.com/Sturmi77/correlcore/issues/782)           |

**Explicit non-goal:** Do not scaffold `apps/web-react` until shared API types exist.

---

## Gap matrix (2026-08-25)

| Dimension             | Good at this maturity                                | Current                                                                                                      | Status  |
| --------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------- |
| Threat model / Art. 9 | Encryption, scrubbing, RLS, rate limits, secret scan | HttpOnly+SameSite, DEK, RLS, SlowAPI, gitleaks                                                               | Strong  |
| Auth maturity         | MFA option, lockout, logout kills access             | JWT cookies + refresh rotate + Content-Type CSRF gate; MFA deferred, access denylist accepted residual (ADR) | Partial |
| Contract discipline   | Generated client or shared package + CI              | Hand DTOs; enum contract only                                                                                | Gap     |
| Module boundaries     | Analytics split; thin routes                         | analytics split into `insights.*`; routes still large                                                        | Partial |
| Test pyramid          | Unit + selective integration + real-API e2e          | Unit excellent; e2e mostly mocked smoke                                                                      | Partial |
| SAST / DAST / images  | CodeQL or Semgrep + image scan                       | CodeQL SAST (#801) + deps audit + gitleaks; no DAST / image scan yet                                         | Partial |
| Observability         | Health + scrubbed errors + job SLOs                  | Health/logs/GlitchTip; no Prometheus by design                                                               | Partial |
| External assurance    | Independent pentest before broad hosted              | Pending (M9)                                                                                                 | Gap     |
| Dual frontend         | Shared packages before second GUI                    | React unscaffolded (correct)                                                                                 | OK      |

---

## Test plan

- `cd backend && uv run --python 3.12 pytest tests/test_auth_service.py tests/test_auth_cookies.py tests/test_settings_cookie_secure.py tests/test_settings_production_guards.py tests/test_media.py tests/test_password_policy.py -q`
- `uv run --python 3.12 ruff check app tests`
- Confirm Dependabot config present: `.github/dependabot.yml`
- Confirm cookie refresh path omits body JWT without `include_access_token`
