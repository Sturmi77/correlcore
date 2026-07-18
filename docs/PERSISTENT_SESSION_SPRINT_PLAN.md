# Persistent Session Sprint Plan — „Angemeldet bleiben“

Last updated: 2026-07-18

Companion to [`docs/features/PERSISTENT_SESSION_PLAN.md`](features/PERSISTENT_SESSION_PLAN.md)
(technical design), [ADR-0006](adr/0006-cookie-auth-mit-capacitor-migration.md),
and Issue [#453](https://github.com/Sturmi77/correlcore/issues/453).

**Goal:** One login checkbox **„Angemeldet bleiben“** that keeps the session
across relaunch on **Web**, **PWA**, and **Capacitor Android** — without storing
passwords or putting JWTs in web `localStorage` / `sessionStorage`.

**Exit criterion (feature):** All acceptance checks in #453 green; ADR-0006
amended; QA matrix signed off for the three surfaces.

**Status:** Planned (design doc landed; implementation not started).

---

## Scope vs non-scope

| In scope | Out of scope (v1) |
| -------- | ----------------- |
| `remember_me` API + login UI | Biometric / Credential Manager |
| Web/PWA session vs persistent cookies | Refresh TTL > 30 days |
| Capacitor EncryptedSharedPreferences restore | iOS Capacitor shell |
| Boot restore before `hydrate()` | Password or DEK in session store |
| Logout clears all session material | Changing ADR-0006 cookie path for browser |

Related but separate: Sprint B widget items (#445–#447) — widget deep-link /
timezone must not block this sprint; widget creds remain a Glance exception,
not a substitute for WebView restore.

---

## Sprint overview

| Sprint | Title | Surfaces | Exit criterion |
| ------ | ----- | -------- | -------------- |
| **PS-0** | Contract lock + UI flag | All | Decisions D1–D7 locked; `remember_me` on login API + checkbox; ADR amend draft |
| **PS-1** | Web + PWA cookie modes | Web, PWA | Remember on/off behaves correctly across browser session and PWA relaunch |
| **PS-2** | Capacitor secure restore | Android APK | Force-stop → reopen stays signed in when remember on; off → login |
| **PS-3** | Hardening, tests, closeout | All | Coverage + security checklist + release notes; #453 closable |

Dependency: **PS-0 → PS-1 ∥ PS-2 prep → PS-2 → PS-3**.  
PS-1 (Web/PWA) can finish before PS-2 native work; PS-2 must not ship without PS-0 flag wiring.  
PS-3 can start test scaffolding during PS-1/PS-2 but closes last.

```text
PS-0 (contract + UI)
   │
   ├──────────────► PS-1 (Web / PWA cookies)
   │
   └──────────────► PS-2 (Capacitor SecureStore + boot restore)
                         │
                         ▼
                      PS-3 (tests, ADR final, QA matrix, closeout)
```

---

## Baseline (before PS-0)

| Item | Status |
| ---- | ------ |
| Web/PWA HttpOnly cookies (`access` 15m, `refresh` 30d) | Done |
| Capacitor Bearer in-memory (`sessionTokens`) | Done |
| Single-flight `/auth/refresh` | Done |
| Cookie JWT body gate on cookie-sourced refresh | Done (#442) |
| Widget SharedPreferences mirror (Glance only) | Done — **not** WebView restore |
| Login „Angemeldet bleiben“ checkbox | Missing |
| Capacitor cold-start session restore | Missing |
| Explicit session-cookie mode (`remember_me=false`) | Missing |

---

## Sprint PS-0 — Contract lock + UI flag

**Maps to:** WP0 in the feature plan  
**Depends on:** #453 accepted; D1–D7 review  
**Primary PR theme:** `feat(auth): remember_me contract`

### Work

- [ ] Lock product decisions D1–D7 (comment on #453 or short table in ADR draft).
- [ ] Backend: add `remember_me: bool = True` to `LoginRequest` (and session-issuing
      flows that should honor it: verify-email / reset-password if they set cookies).
- [ ] Backend: thread flag into `set_auth_cookies` (no behavior change yet if default
      matches today’s `max_age` — or stub and implement fully in PS-1).
- [ ] Frontend login: checkbox + i18n DE/EN; persist UX preference only as
      `localStorage` key `cc_remember_me` (never tokens).
- [ ] Pass `remember_me` from `login()` → API.
- [ ] Draft ADR-0006 amendment section (persistent Capacitor store + session cookies).
- [ ] Document Homelab `COOKIE_SECURE` pitfall in plan/QA (no silent “always login”
      when cookies were never stored).

### Exit

- [ ] Login UI shows checkbox (default on).
- [ ] API accepts `remember_me`; OpenAPI / schema tests green.
- [ ] No regression: Capacitor and cookie login still work with default `true`.

### Out of scope here

- EncryptedSharedPreferences implementation (PS-2).
- Changing cookie `Max-Age` behavior (PS-1).

---

## Sprint PS-1 — Web + PWA cookie modes

**Maps to:** WP1  
**Depends on:** PS-0  
**Primary PR theme:** `feat(auth): session vs persistent cookies`

### Work

- [ ] `set_auth_cookies(..., remember_me: bool)`:
  - `true` → current `max_age` (persistent).
  - `false` → session cookies (omit `max_age`).
- [ ] Honor flag on login / verify-email / reset-password cookie issuance.
- [ ] Document refresh re-set behavior (v1: session cookies live until browser
      process end; refresh may re-issue with same practical lifetime).
- [ ] Backend tests: `Set-Cookie` with/without `Max-Age`.
- [ ] Web E2E (or Playwright smoke): login remember on → reload → authenticated.
- [ ] Manual PWA QA checklist (same origin as `/api/v1` proxy):
  - [ ] Install → login remember on → force-stop standalone → reopen → signed in.
  - [ ] Remember off → end browser/PWA session → signed out.
  - [ ] Confirm SW still skips `/api/*` ([`docs/features/PWA.md`](features/PWA.md)).
- [ ] Note iOS “Add to Home Screen” / ITP limits in QA notes if observed.

### Exit

- [ ] Web remember on/off matches acceptance in #453.
- [ ] PWA standalone relaunch verified (or documented blocker with issue link).
- [ ] Cookie Secure/Homelab guidance linked from selfhost docs if missing.

### Out of scope here

- Capacitor secure store (PS-2).

---

## Sprint PS-2 — Capacitor secure restore

**Maps to:** WP2  
**Depends on:** PS-0 (flag + login payload); ideally PS-1 merged or not conflicting  
**Primary PR theme:** `feat(android): secure session restore`

### Work

- [ ] Native secure store (Android): `EncryptedSharedPreferences` / Keystore-backed
      plugin or Kotlin bridge (`refresh_token`, optional `access_token`, `api_base`,
      `remember_me`).
- [ ] JS module (`secureSession.ts` or extend `sessionTokens.ts`):
      `persist` / `restore` / `clear`.
- [ ] On `setSessionTokens`: if Capacitor && remember → write secure store;
      keep or gate widget mirror (default: mirror only when remember on).
- [ ] On logout / failed refresh: clear memory + secure store + widget creds.
- [ ] Boot order in `+layout.svelte` (Capacitor only):
      `restoreSession()` → memory → optional `/auth/refresh?include_access_token=true`
      → `hydrate()`.
- [ ] Unit tests with mocked native bridge.
- [ ] Device QA script in `docs/selfhost/ANDROID_SIDELOAD.md` or feature plan appendix:
  - force-stop with remember on/off
  - logout clears relaunch session
  - API base still restored with tokens

### Exit

- [ ] APK: remember on → force-stop → reopen → Home without password.
- [ ] APK: remember off → force-stop → login screen.
- [ ] Logout → relaunch → login screen; no stale refresh in secure store.

### Out of scope here

- iOS Keychain path.
- Biometrics.

---

## Sprint PS-3 — Hardening, tests, closeout

**Maps to:** WP3  
**Depends on:** PS-1 + PS-2  
**Primary PR theme:** `test(auth): persistent session closeout` (+ docs)

### Work

- [ ] Finalize ADR-0006 amendment (Accepted).
- [ ] Mark [`PERSISTENT_SESSION_PLAN.md`](features/PERSISTENT_SESSION_PLAN.md) status
      **Done**; fill status table.
- [ ] Regression pack: single-flight refresh; cookie body JWT gate; push unregister
      order on logout; widget creds cleared with session.
- [ ] Security checklist from feature plan all checked.
- [ ] CHANGELOG / release-notes blurb for next `v*` tag.
- [ ] Cross-surface QA matrix (sign-off):

| Check | Web | PWA | Capacitor |
| ----- | --- | --- | --------- |
| Remember on survives relaunch | ☐ | ☐ | ☐ |
| Remember off does not | ☐ | ☐ | ☐ |
| Logout clears session | ☐ | ☐ | ☐ |
| No JWT in web storage | ☐ | ☐ | ☐ |
| Offline/network during hydrate (document behavior) | ☐ | ☐ | ☐ |

### Exit

- [ ] #453 acceptance criteria all checked.
- [ ] This sprint plan status → **Complete**.
- [ ] No open P0/P1 auth regressions from the change set.

---

## Risks & mitigations

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| HTTP Homelab drops `Secure` cookies | Web/PWA look “broken” (always login) | PS-0/PS-1 docs + `COOKIE_SECURE` guidance; QA on HTTPS and known HTTP setups |
| Secure store / widget double-write races | Stale refresh, revoke_all | Single write path; prefer body refresh when Capacitor opt-in (existing hardening) |
| `hydrate()` treats network error as anonymous | False logout offline | Document in PS-3; optional follow-up issue if PWA offline UX suffers |
| Scope creep into biometrics / longer TTL | Delays APK fix | Keep out of scope; track as follow-ups on #453 |

---

## Definition of Done (per sprint PR)

- [ ] Tests for touched auth paths green (pytest / vitest / relevant e2e)
- [ ] No JWTs introduced into `localStorage` / `sessionStorage`
- [ ] Logout clears the storage backend that sprint owns
- [ ] Docs updated (ADR draft or final; sideload/PWA notes as needed)
- [ ] Issue #453 checklist items updated for that sprint’s surface

---

## Issue & doc index

| Artifact | Role |
| -------- | ---- |
| [#453](https://github.com/Sturmi77/correlcore/issues/453) | Feature tracking + acceptance |
| [`docs/features/PERSISTENT_SESSION_PLAN.md`](features/PERSISTENT_SESSION_PLAN.md) | Technical design (WP0–WP3, architecture) |
| This file | Sprint sequencing + exit criteria |
| ADR-0006 | Auth storage policy (amend in PS-0/PS-3) |
| [#452](https://github.com/Sturmi77/correlcore/issues/452) | M11 polish B/C — parallel, not blocking |

---

## Suggested PR slicing

| Sprint | Suggested PR title |
| ------ | ------------------ |
| PS-0 | `feat(auth): remember_me flag + login checkbox (#453)` |
| PS-1 | `feat(auth): session vs persistent cookies for Web/PWA (#453)` |
| PS-2 | `feat(android): EncryptedSharedPreferences session restore (#453)` |
| PS-3 | `docs+test(auth): persistent session closeout (#453)` |
