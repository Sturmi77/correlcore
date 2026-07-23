# Persistent Session — Cross-Surface QA Checklist

**Feature:** „Angemeldet bleiben" across Web, PWA and Capacitor Android
**Tracker:** [#453](https://github.com/Sturmi77/correlcore/issues/453)
**Plans:** [`PERSISTENT_SESSION_PLAN.md`](../features/PERSISTENT_SESSION_PLAN.md) · [`PERSISTENT_SESSION_SPRINT_PLAN.md`](../PERSISTENT_SESSION_SPRINT_PLAN.md) · [ADR-0006](../adr/0006-cookie-auth-mit-capacitor-migration.md)
**Date:** 2026-07-23

PS-0…PS-3 are in code. This is the manual pass that #453 lists as its remaining
exit criterion — it cannot run in CI, which has no real cookie jar, no installed
PWA and no Android device.

---

## Automated coverage (already green)

| Check                                                | Where                                        |
| ---------------------------------------------------- | -------------------------------------------- |
| `remember_me=false` → `Set-Cookie` without `Max-Age` | `test_auth.py`, `test_auth_cookies.py`       |
| `remember_me=true` → `Max-Age` present               | `test_auth.py`, `test_auth_cookies.py`       |
| Remember-me preference is a UX flag only             | `rememberMePreference.test.ts`               |
| Secure store persist / restore / clear               | `secureSession.test.ts`                      |
| No auth material in web storage                      | `pnpm check:no-token-storage` (CI guardrail) |

The web E2E suite runs against mocked API routes with no backend, so the
"login → reload → `/auth/me` 200" row from the plan's WP3 table cannot be
meaningfully automated in this harness — it is covered manually below.

---

## Sign-off matrix

Fill in during the pass. A row is only green when observed, not inferred.

| Check                                      | Web | PWA | Capacitor |
| ------------------------------------------ | --- | --- | --------- |
| Remember **on** survives relaunch          | ☐   | ☐   | ☐         |
| Remember **off** does not survive          | ☐   | ☐   | ☐         |
| Logout clears the session                  | ☐   | ☐   | ☐         |
| No JWT in web storage (DevTools)           | ☐   | ☐   | n/a       |
| Network loss during hydrate behaves sanely | ☐   | ☐   | ☐         |

---

## Web (browser)

1. Log in with **„Angemeldet bleiben" on** → close the tab → reopen the app URL.
   Expect: still signed in, no password prompt.
2. DevTools → Application → Local/Session Storage. Expect: `cc_remember_me`,
   `cc_last_user` and UI preferences only — **no** `access_token` /
   `refresh_token` / JWT-shaped values anywhere.
3. DevTools → Application → Cookies. Expect: `access` and `refresh` are
   `HttpOnly`, and both carry an `Expires`/`Max-Age`.
4. Log out → reload. Expect: login screen, auth cookies gone.
5. Log in with **remember off** → check cookies: **no** `Max-Age` (shown as
   "Session"). Quit the browser entirely → reopen. Expect: signed out.

> **Homelab pitfall:** over plain HTTP with `COOKIE_SECURE=true`, the browser
> silently drops the auth cookies and every launch looks like "remember is
> broken". Verify `COOKIE_SECURE` matches the scheme actually in use before
> filing a bug.

## PWA (installed, standalone)

6. Install the PWA from the **same origin** that serves `/api/v1`.
7. Log in with remember on → force-stop / swipe the app away → reopen.
   Expect: still signed in.
8. Confirm the service worker still skips `/api/*` (see
   [`PWA.md`](../features/PWA.md)) — a cached `/auth/me` would fake a pass here.
9. iOS "Add to Home Screen": Safari ITP may clear cookies on its own schedule.
   Record what you observe rather than treating it as pass/fail.

## Capacitor Android

10. Sign in with remember on → force-stop the app from Android settings →
    reopen. Expect: lands authenticated, no password prompt.
11. Sign in with remember **off** → force-stop → reopen. Expect: login required.
12. Log out → force-stop → reopen. Expect: login required, and the homescreen
    widget shows its signed-out state (secure store **and** widget credentials
    cleared).
13. Airplane mode → cold start with remember on. Expect: the shell restores the
    last known user for offline use rather than bouncing to login; going online
    reconciles. Record the actual behaviour.

---

## Result

- Date / build:
- Tester:
- Failures found:

Close #453 only when every applicable row above is observed green.
