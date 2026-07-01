# Mobile Web Closeout — Cross-Phase QA (Sprint C)

Date: 2026-06-27  
Scope: Phases 0–4 mobile code paths (Entry, Trends, Insights, Settings/PWA,
supporting flows). Figma references: Sprint 1 `48:1089`, Sprint 2 `59:1285`,
Sprint 3 `98:1573`, Sprint 4 `105:1626`.

**Result: Sprint C cross-phase mobile QA closeout passed.**

Code reference: `main` @ `d77b556`.

---

## Evidence summary

| Layer            | Method                                                         | Result                                       |
| ---------------- | -------------------------------------------------------------- | -------------------------------------------- |
| E2E mobile suite | 17 Playwright specs (`mobile-*`, `m7-insights-mobile`)         | **17/17 pass** (local, serial, 2026-06-27)   |
| Shell contract   | Vitest `surface-contract.test.ts`, `appNav.test.ts`            | 8/8 pass                                     |
| Component smoke  | `MobileTrendsSummary`, `MobileInsightLead`                     | 4/4 pass                                     |
| Phase 3 QA       | [`MOBILE_INSIGHTS_PHASE3_QA.md`](MOBILE_INSIGHTS_PHASE3_QA.md) | Prior sign-off retained                      |
| Figma parity     | Sprint 1–4 flow boards                                         | Signed off 2026-06-26                        |
| Theme parity     | ADR-0027 contrast CI + semantic tokens                         | Default E2E theme; dark via token contract\* |

\*Dark/light rendered matrix: E2E runs default (light) theme. No viewport-specific
theme regressions observed; contrast gate enforced in CI.

**E2E execution note:** Run mobile specs with `--workers=1` (or
`npm run test:e2e:mobile`) to avoid cold-start timeouts when the Vite dev server
boots in parallel workers. Default Playwright worker count may flake on first tests.

---

## Viewport matrix

Mandatory: **390 × 844**, **430 × 932**. Sanity: **1280 × 900** (mobile surfaces
hidden, desktop composition preserved). Optional manual: **768 × 1024** (shell
rail transition — covered by CSS breakpoint contract @ 768 px).

| Flow              | 390 L | 430 L | 1280 L | H-scroll | Touch ≥44 px | E2E spec                                           |
| ----------------- | ----- | ----- | ------ | -------- | ------------ | -------------------------------------------------- |
| Entry             | ✓     | ✓     | ✓      | ✓        | ✓            | `mobile-entry-foundation`                          |
| Trends            | ✓     | ✓     | ✓      | ✓        | ✓ (toggle)   | `mobile-trends-foundation`                         |
| Insights          | ✓     | ✓     | ✓      | ✓        | ✓ (M7 touch) | `mobile-insights-foundation`, `m7-insights-mobile` |
| Settings / PWA    | ✓     | ✓     | ✓      | ✓        | ✓            | `mobile-supporting-flows`                          |
| Onboarding / Auth | ✓†    | ✓†    | —      | ✓†       | ✓†           | Figma + route code†                                |
| App shell / Nav   | ✓‡    | ✓‡    | ✓‡     | ✓‡       | ✓‡ (CSS)     | Contract tests‡                                    |

† **Onboarding / Auth:** No dedicated Playwright file yet. Code routes exist;
Figma Sprint 4 frames (`105:1978`–`105:2164`, B4–B5) signed off. Manual spot-check
recommended for verify/resend state permutations before production release.

‡ **App shell:** `AppNav` min 44 px targets in `app.css`; bottom nav at &lt;768 px,
side rail at ≥768 px. Validated via `surface-contract.test.ts` + layout CSS.

---

## Per-flow assertions

### Entry (`/entries/new`, `/entries/day/[date]`)

- Mobile: tags/symptoms always visible; `entry-optional-extras-toggle` ≥44 px for note/cycle only;
  tags/symptoms reachable after expand; no page-level horizontal overflow.
- Offline: explicit banner + retry; no silent queue (ADR-0009).
- Desktop (1280): no compact toggle; tag section visible without expand.
- Read-only: historical day outside 7-day window shows read-only state.

### Trends (`/trends`)

- Mobile: `mobile-trends-summary` first; detail canvas behind explicit toggle;
  empty summary state; range controls work.
- Desktop: full `trends-compare-panel` visible; mobile summary hidden.

### Insights (`/insights`)

- Mobile 390: `mobile-insight-lead` before view tabs; confidence + maturity;
  no duplicate percent badge; no horizontal overflow.
- Mobile 430: matrix tab hides lead; findings restores lead; symptom feed +
  “Deepen analysis” reachable via touch. Figma: Matrix · 430 (`121:2781`).
- Desktop 1280: no `mobile-insight-lead`; stage header + four-card feed;
  matrix tab works.

### Settings / PWA (`/settings`, `/settings/symptoms`, `/settings/app`)

- Mobile: Settings links to symptom management and App & Offline; stacked
  management layout; no horizontal overflow.
- Offline: global `pwa-offline-banner` with ≥44 px retry control.
- Desktop: dense symptom management row layout preserved.

### Onboarding / Auth (manual + Figma)

| Route                       | Figma node (Sprint 4)  | Code status                     |
| --------------------------- | ---------------------- | ------------------------------- |
| `/onboarding`               | `105:2176`, `105:2140` | Touch targets, stacked actions  |
| `/onboarding/profile`       | `105:2152`             | 44 px controls                  |
| `/auth/verify-email`        | `105:1978`–`105:2088`  | Idle/busy/success/error/missing |
| `/auth/resend-verification` | `105:2119`, `105:2127` | Success/error                   |
| PWA overlays (shell)        | `105:2190`, `105:2228` | Offline + update banners        |

---

## Static gates (2026-06-27)

| Gate                          | Result    |
| ----------------------------- | --------- |
| `npm run test:e2e:mobile`     | 17 passed |
| `surface-contract.test.ts`    | 3 passed  |
| `appNav.test.ts`              | 5 passed  |
| `MobileTrendsSummary.test.ts` | 2 passed  |
| `MobileInsightLead.test.ts`   | 2 passed  |

---

## Known deferrals (not blocking mobile closeout)

- Password recovery route (backend contract pending)
- Reminders and account deletion settings placeholders
- Dexie / background sync queue (ADR-0009 — Entry-owned retry only)
- Phase 5 desktop consolidation (wide-screen density)
- Published-library Code Connect activation — **Sprint H deferred** (Figma Dev/Full seat). See [`FIGMA_PRODUCTION_GRADE_QA.md`](FIGMA_PRODUCTION_GRADE_QA.md).
- Dedicated Playwright coverage for full auth/onboarding state matrix

Track defects with GitHub label `mobile` if found post-release.

---

## Sign-off

Cross-phase mobile QA for **Phases 0–4** is **complete** for automated regression
and documented manual gaps. Next track: **Sprint D** (audit doc refresh, GitHub
issue closure, optional Code Connect template).
