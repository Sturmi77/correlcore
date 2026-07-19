# Persistent Session („Angemeldet bleiben“) — Implementation Plan

Status: **Implemented** (PS-0…PS-3 in code; device QA still recommended)  
Last updated: 2026-07-18  
Related: ADR-0006, ADR-0004, Issue [#453](https://github.com/Sturmi77/correlcore/issues/453)  
Surfaces: **Web (browser)**, **PWA (standalone)**, **Capacitor Android**  
**Sprint plan:** [`docs/PERSISTENT_SESSION_SPRINT_PLAN.md`](../PERSISTENT_SESSION_SPRINT_PLAN.md) (PS-0 … PS-3)

---

## Goal

After a successful login with **„Angemeldet bleiben“** enabled (default on), the
user can close the tab / kill the PWA / restart the Android app and return
**without re-entering email/password**, until:

- the refresh token expires (~30 days today), or
- the user logs out, or
- the refresh token is revoked (replay, password reset, account delete).

One product contract; three storage backends.

---

## Current state

| Surface                            | Auth mechanism (ADR-0006)                                         | Survives restart today?         | Main gap                                                                                                 |
| ---------------------------------- | ----------------------------------------------------------------- | ------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Web** (same-origin `/api/v1`)    | HttpOnly cookies (`access` 15m, `refresh` 30d, `SameSite=Strict`) | **Yes**, if cookies stick       | No explicit remember-me; silent failures when `Secure` cookies are dropped on HTTP; no session-only mode |
| **PWA** (installed, same origin)   | Same cookie jar as the installing origin                          | **Yes**, same as Web            | Must verify standalone relaunch; SW must keep skipping `/api/*` (already true)                           |
| **Capacitor** (`VITE_CAPACITOR=1`) | Bearer JWTs in JS memory only                                     | **No** — cold start → anonymous | No secure restore of refresh token into WebView before `hydrate()`                                       |

Shared boot path today: `hydrate()` → `GET /auth/me` (with single-flight refresh on 401).  
Capacitor has no refresh material after process death → login every launch.

Widget prefs already mirror access+refresh for Glance (`WidgetCredentialsStore`) — that is a
**widget** exception, not a WebView session restore.

---

## Product decisions (locked — Issue #453 / ADR-0006 amendment)

| ID  | Topic            | Proposal                                                                                                                      |
| --- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| D1  | Default          | **„Angemeldet bleiben“ = on** for all surfaces                                                                                |
| D2  | Off meaning      | Web/PWA: **session cookies** (no `Max-Age` / browser-session). Capacitor: memory-only (current behavior)                      |
| D3  | On meaning       | Web/PWA: persistent cookies (`Max-Age` = refresh TTL). Capacitor: refresh in **EncryptedSharedPreferences** (Keystore-backed) |
| D4  | Password storage | **Never** store password; only refresh (and short-lived access as needed)                                                     |
| D5  | Web storage      | **Never** `localStorage` / `sessionStorage` for JWTs (ADR-0006 stands)                                                        |
| D6  | Refresh TTL      | Keep `JWT_REFRESH_TOKEN_EXPIRE_DAYS=30` for v1; optional longer TTL later                                                     |
| D7  | UX copy          | Login checkbox + short help; Settings can show “signed in until …” later (optional)                                           |

---

## Architecture

```text
                    ┌─────────────────────────────┐
                    │  Login (+ remember_me flag) │
                    └──────────────┬──────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
     Web / PWA               Capacitor                Shared
     cookie path             Bearer path              hydrate()
           │                       │                       │
           ▼                       ▼                       ▼
  set_auth_cookies          setSessionTokens         GET /auth/me
  (session | persistent)    + SecureStore.write      (+ refresh on 401)
           │                       │
           ▼                       ▼
  Browser cookie jar        EncryptedSharedPreferences
           │                       │
           └───────────┬───────────┘
                       ▼
              App relaunch / PWA open
                       │
         restore refresh material
         (cookies automatic | SecureStore → memory)
                       │
                       ▼
                   hydrate()
```

### Platform matrix

| Concern         | Web                   | PWA        | Capacitor                                                             |
| --------------- | --------------------- | ---------- | --------------------------------------------------------------------- |
| Persist refresh | HttpOnly cookie       | Same       | Native secure store                                                   |
| Persist access  | HttpOnly cookie (15m) | Same       | Memory (+ optional native cache for widget only)                      |
| `credentials`   | `include`             | `include`  | `omit` + `Authorization`                                              |
| Boot restore    | Cookie jar            | Cookie jar | Read SecureStore → `setSessionTokens` → refresh if needed → `hydrate` |
| Logout          | `clear_auth_cookies`  | Same       | Clear memory + SecureStore + widget creds                             |
| Remember off    | Session cookies       | Same       | Skip SecureStore write                                                |

---

## Work packages

### WP0 — Contract & diagnostics (all surfaces)

1. Amend **ADR-0006** with persistent-session exception for Capacitor secure storage;
   document Web session vs persistent cookies.
2. Add `remember_me: bool = true` to `LoginRequest` (and verify-email / reset-password
   session establishment if those issue cookies/tokens the same way).
3. Login UI: checkbox bound to `remember_me`; i18n DE/EN.
4. Ops note: document `COOKIE_SECURE` / HTTP Homelab so Web/PWA cookies are not
   silently discarded (existing ADR-0006 Secure fix — call out in QA).

**Exit:** API accepts flag; UI ships; docs updated; no behavior change yet beyond
passing the flag through (safe default `true` = today’s cookie max-age).

---

### WP1 — Web + PWA cookie modes

**Backend (`set_auth_cookies` / login / refresh / verify / reset):**

- When `remember_me=true` (default): keep current `max_age` on access + refresh.
- When `remember_me=false`: set cookies **without** `max_age` (session cookies).
- Refresh responses: if the session was established as session-only, re-issue
  session cookies (thread a flag via cookie attribute or server-side session
  metadata — prefer: omit `max_age` on every `set_auth_cookies` call for that
  response chain; store `remember_me` preference is **not** required server-side
  if each login sets the cookie mode and refresh copies request cookie presence).

  Practical approach for v1:

  - Login/verify/reset: honor `remember_me` when setting cookies.
  - Refresh: if the incoming refresh cookie had no expiry tracking, browsers still
    send session cookies until browser exit — re-set cookies with the same mode.
  - Simplest v1: refresh always sets **persistent** cookies if a refresh cookie
    was present (session cookies already die on browser close). Document that
    “remember off” lasts until browser/PWA process end, not until next refresh.

**Frontend:**

- Pass `remember_me` on login.
- Persist checkbox preference in `localStorage` as `cc_remember_me` (boolean UX
  only — **not** tokens).
- Ensure `hydrate()` remains the single boot entry; do not treat network errors
  during offline as hard logout if offline sync is enabled (optional follow-up:
  distinguish 401 vs network — today network → anonymous; may annoy PWA offline
  — track separately if needed).

**PWA-specific QA:**

- Install PWA from same origin as API proxy (`/api/v1`).
- Login with remember on → force-stop / swipe away → reopen → still authenticated.
- Confirm SW does not cache `/api/*` (`docs/features/PWA.md`).
- iOS “Add to Home Screen”: cookie persistence is OS-dependent; document known
  limits if Safari ITP clears cookies.

**Exit:** Web + installed PWA keep session across relaunch when remember is on;
session-only when off; E2E smoke for cookie login + reload.

---

### WP2 — Capacitor secure restore

1. **Native secure store** (Android first): Capacitor plugin or thin Kotlin bridge
   using `EncryptedSharedPreferences` (or Jetpack Security Crypto).
   - Keys: `refresh_token`, optional `access_token`, `api_base`, `remember_me`.
   - Encrypt at rest via Android Keystore.
2. **JS API** (`apps/web/src/lib/api/secureSession.ts` or extend `sessionTokens.ts`):
   - `persistSession({ refresh, access?, remember })`
   - `restoreSession(): Promise<Tokens | null>`
   - `clearPersistedSession()`
3. **Wire-up:**
   - `setSessionTokens`: if Capacitor && remember → write secure store (and keep
     widget mirror as today).
   - `clearSessionTokens` / logout: clear secure store.
   - **Before** `hydrate()` in `+layout.svelte` (Capacitor only): `restoreSession()`
     → memory → optional proactive `/auth/refresh?include_access_token=true` if
     access missing/expired → then `hydrate()`.
4. Prefer **body refresh** over leftover cookies when both present (already
   tightened in trends/auth hardening); Capacitor uses `credentials: 'omit'`.
5. If remember is off: never write secure store; widget mirror policy TBD
   (recommend: widget only when remember on, or widget keeps its own short-lived
   mirror — product call; default: mirror only when remember on).

**Exit:** Kill Android app → reopen → landed authenticated without password;
logout clears store; failed refresh clears store and shows login.

---

### WP3 — Hardening & tests

| Layer      | Tests                                                                              |
| ---------- | ---------------------------------------------------------------------------------- |
| Backend    | Login `remember_me=false` → `Set-Cookie` without Max-Age; `true` → Max-Age present |
| Web unit   | Checkbox preference; login payload includes flag                                   |
| Web E2E    | Login → reload → `/auth/me` still 200 (cookie path)                                |
| Capacitor  | Unit/mock restore/persist/clear; manual QA script on device                        |
| Regression | Refresh single-flight; cookie JWT body gate; logout clears push + tokens           |

Security checklist:

- [ ] No JWT in `localStorage` / `sessionStorage`
- [ ] Secure store cleared on logout and refresh replay/401
- [ ] Production still forces `COOKIE_SECURE` for Web/PWA
- [ ] ADR-0006 updated; WIDGET.md notes relationship to WebView restore

---

## Suggested implementation order

Mapped 1:1 to sprints in
[`PERSISTENT_SESSION_SPRINT_PLAN.md`](../PERSISTENT_SESSION_SPRINT_PLAN.md):

| WP  | Sprint   | Focus                    |
| --- | -------- | ------------------------ |
| WP0 | **PS-0** | Contract + UI flag       |
| WP1 | **PS-1** | Web/PWA cookie modes     |
| WP2 | **PS-2** | Capacitor secure restore |
| WP3 | **PS-3** | Hardening + closeout     |

Capacitor-only would leave Web/PWA remember-me undefined and miss cookie-mode /
Secure diagnostics; this order keeps one checkbox and one mental model.

---

## Out of scope (v1)

- Biometric unlock / OS credential manager for password autofill (nice follow-up)
- Extending refresh TTL beyond 30 days
- iOS Capacitor (same design when iOS shell exists)
- Storing passwords or DEK material in the session store

---

## Acceptance criteria (issue-level)

- [ ] Login shows „Angemeldet bleiben“ (default on); preference remembered as UX flag only
- [ ] **Web:** remember on → close tab / new tab → still signed in (within refresh TTL)
- [ ] **Web:** remember off → quit browser session → signed out
- [ ] **PWA:** remember on → force-stop / reopen standalone → still signed in
- [ ] **Capacitor:** remember on → force-stop app → reopen → still signed in
- [ ] **Capacitor:** remember off → force-stop → login required
- [ ] Logout clears cookies (Web/PWA) and secure store + widget creds (Capacitor)
- [ ] No tokens in web `localStorage` / `sessionStorage`
- [ ] ADR-0006 amended; this plan marked done when WP0–WP3 land

---

## References

- [`docs/PERSISTENT_SESSION_SPRINT_PLAN.md`](../PERSISTENT_SESSION_SPRINT_PLAN.md)
- [`docs/adr/0006-cookie-auth-mit-capacitor-migration.md`](../adr/0006-cookie-auth-mit-capacitor-migration.md)
- [`docs/features/PWA.md`](PWA.md)
- [`docs/features/WIDGET.md`](WIDGET.md)
- `apps/web/src/lib/api/sessionTokens.ts`, `client.ts`, `stores/auth.ts`
- `backend/app/core/auth_cookies.py`
