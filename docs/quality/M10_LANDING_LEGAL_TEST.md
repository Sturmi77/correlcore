# M10 Landing & Legal Test Protocol

Last updated: 2026-07-11  
Sprint: M10-S4 (Landing & legal)

## Objective

Verify marketing landing replaces pre-alpha home, `/impressum` exists, and privacy
links are reachable from landing and auth footer (DSGVO checkpoint M10).

## Scope

| In scope                                          | Out of scope                               |
| ------------------------------------------------- | ------------------------------------------ |
| Landing page for anonymous `/`                    | Operator-specific imprint customization UI |
| `/impressum` route (AT/DE template)               | Landing page visual QA sign-off (Sprint 6) |
| `/privacy` public access                          | Custom domain docs                         |
| Legal footer on landing, privacy, impressum, auth |                                            |

## Static checks

- [x] `LandingPage.svelte` replaces pre-alpha badge
- [x] `isPublicRoute('/privacy')` and `isPublicRoute('/impressum')`
- [x] `landing-legal.test.ts` contract tests
- [x] i18n keys in `en.json` and `de.json`

## Manual / E2E verification

1. Open `/` while logged out → marketing landing with feature cards
2. Footer links: Privacy, Impressum, Documentation, Source
3. `/privacy` loads without login redirect
4. `/impressum` loads without login redirect
5. `/auth/login` footer shows Privacy + Impressum links

## Operator note

Selfhost operators must publish their own operator name, address, and contact on
the instance Impressum before public production use. The shipped template explains
this obligation.

## Sign-off

| Check                    | Status | Date       |
| ------------------------ | ------ | ---------- |
| Landing component        | PASS   | 2026-07-11 |
| Impressum route          | PASS   | 2026-07-11 |
| Public privacy/impressum | PASS   | 2026-07-11 |
| Auth footer links        | PASS   | 2026-07-11 |
| Rendered visual QA       | PASS   | 2026-07-11 — [`M10_VISUAL_QA.md`](M10_VISUAL_QA.md) |
