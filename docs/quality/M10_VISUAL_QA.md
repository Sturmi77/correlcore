# M10 Visual QA Closeout

Date: 2026-07-11

Scope: Marketing landing, legal pages (privacy, impressum), docs site build, and
release-engineering documentation for public selfhost v1.0 (M10 Sprints 4–6).
Core authenticated flows remain covered by existing `smoke.spec.ts`.

## Result

**M10 GUI QA: passed.**

No critical blocker was found. Anonymous landing renders with legal footer links,
public privacy/impressum routes pass contract tests, MkDocs site builds strict,
and compose configs validate. Remaining items are operator actions (live VPS stack,
image publish to Docker Hub, GitHub Pages deploy, final tag push) — not functional
blockers for M10 exit.

## Test Environment

| Area | Detail |
| ---- | ------ |
| Web unit | Vitest — `landing-legal.test.ts`, `noGamificationCopy.test.ts` |
| Web E2E | Playwright smoke at `http://127.0.0.1:4173` (3 tests) |
| Docs | `mkdocs build --strict` in `docs-site/` |
| Compose | `docker compose config` for production + quickstart |
| Locale | EN + DE i18n keys verified in contract tests |
| M10 phase | Sprint 6 closeout |

## GUI Coverage — Landing & legal (Sprint 4)

| Surface | Result | Evidence |
| ------- | ------ | -------- |
| Anonymous `/` marketing landing | Pass | `landing-legal.test.ts` — `LandingPage`, no pre-alpha badge |
| Register / login CTAs | Pass | `data-testid="landing-cta-register"`, `landing-cta-login` |
| Legal footer — privacy | Pass | `data-testid="legal-footer-privacy"` on landing, privacy, impressum |
| Legal footer — impressum | Pass | `data-testid="legal-footer-impressum"` |
| `/privacy` public access | Pass | `isPublicRoute` + page renders `LegalFooter` |
| `/impressum` AT/DE template | Pass | operator + dispute sections, i18n EN/DE |
| Auth layout footer links | Pass | `auth-footer-privacy`, `auth-footer-impressum` |
| No-gamification copy guard | Pass | `noGamificationCopy.test.ts` — landing daily card rephrased |

## GUI Coverage — Core smoke (regression)

| Route / surface | Result | Notes |
| --------------- | ------ | ----- |
| `/auth/login` | Pass | Redirects to protected workflow |
| `/entries/new` | Pass | Autosave for daily metrics |
| `/trends`, `/insights` | Pass | Authenticated analytics surfaces render |

## Documentation & release flows (Sprints 1–3 + 5–6)

Checklist review (no live VPS required for M10 exit):

| Doc / flow | Result | Notes |
| ---------- | ------ | ----- |
| [`selfhost/INSTALL.md`](../selfhost/INSTALL.md) Path B (quickstart) | Pass | Bootstrap + quickstart compose first |
| [`selfhost/INSTALL.md`](../selfhost/INSTALL.md) Path A (VPS) | Pass | Production compose, Traefik, no MinIO |
| [`selfhost/CONTAINER_IMAGES.md`](../selfhost/CONTAINER_IMAGES.md) | Pass | GHCR + optional Docker Hub |
| [`selfhost/GO_PUBLIC_CHECKLIST.md`](../selfhost/GO_PUBLIC_CHECKLIST.md) | Pass | rc + final tag procedure |
| [`docs-site/`](../docs-site/) MkDocs pages | Pass | install, user guide, API, privacy |
| [`M10_COMPOSE_SMOKE_TEST.md`](M10_COMPOSE_SMOKE_TEST.md) | Pass | config validation |
| [`M10_QUALITY_GATE.md`](M10_QUALITY_GATE.md) | Pass | CQR + SA sign-off |

## Follow-ups (post-M10, non-blocking)

| Item | Target |
| ---- | ------ |
| Live quickstart stack smoke on VPS/homelab | Operator — [`M10_COMPOSE_SMOKE_TEST.md`](M10_COMPOSE_SMOKE_TEST.md) |
| Docker Hub push after secrets configured | Operator — [`M10_RELEASE_PUBLISH_TEST.md`](M10_RELEASE_PUBLISH_TEST.md) |
| Tag `v1.0.0` + GitHub Release | Maintainer — post-merge |
| Operator-specific Impressum details | Selfhost operator before public production |
| Compose profile unification (proposal A) | M10.1 |

## Sign-off

M10 visual QA **approved** for milestone closeout (2026-07-11).
