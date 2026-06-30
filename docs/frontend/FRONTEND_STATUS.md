# CorrelCore — Frontend Status Audit

**Date:** 2026-06-27  
**Run id:** `frontend-status-audit-2026-06-27-v1`  
**Stack:** SvelteKit 2 · Vite · TypeScript · Tailwind 4 · Playwright · Vitest  
**Canonical machine-readable matrix:** [`apps/web/figma/mobile-web-audit.json`](../../apps/web/figma/mobile-web-audit.json)

This document is the **single snapshot** of frontend readiness for production deploy,
design-system parity, and remaining work. It supersedes scattered status lines in
older milestone docs where they conflict.

---

## Executive summary

| Dimension                           | Verdict      | Notes                                                                                               |
| ----------------------------------- | ------------ | --------------------------------------------------------------------------------------------------- |
| **Production deploy (app)**         | **Go**       | Mobile daily-use paths complete; CI gates cover lint, types, unit tests, contrast, build, smoke E2E |
| **Mobile closeout (Phases 0–4)**    | **Complete** | Signed off [`MOBILE_WEB_CLOSEOUT_QA.md`](../quality/MOBILE_WEB_CLOSEOUT_QA.md)                      |
| **Design system (Figma E–G, I)**    | **Complete** | Signed off [`FIGMA_PRODUCTION_GRADE_QA.md`](../quality/FIGMA_PRODUCTION_GRADE_QA.md)                |
| **Code Connect live (Sprint H)**    | **Deferred** | 20 local templates; publish needs Dev/Full seat + token — **not a deploy blocker**                  |
| **Desktop consolidation (Phase 5)** | **Open**     | Entry workspace density, auth web polish — intentional follow-up                                    |

**Operating model:** One SvelteKit codebase. Mobile = capture, check-in, lightweight
review @390/430 px. Web = analysis, comparison, management @1280+ px. Shell switches
at **768 px** (bottom nav → side rail). See [ADR-0017](../adr/0017-frontend-screen-architecture.md).

---

## Deploy readiness

### Required for production (all satisfied)

| Gate                   | Command / job          | Local evidence (2026-06-27)                              |
| ---------------------- | ---------------------- | -------------------------------------------------------- |
| Lint + Svelte check    | `pnpm lint`            | CI `ci-web.yml`                                          |
| Format                 | `pnpm format:check`    | CI                                                       |
| Typecheck              | `pnpm typecheck`       | CI                                                       |
| Unit / component tests | `pnpm test`            | **97 files, 473 tests passed**                           |
| Contrast (ADR-0027)    | `pnpm check:contrast`  | CI (source tokens; avoid stale `apps/web/build` locally) |
| Production build       | `pnpm build`           | CI                                                       |
| E2E smoke              | `pnpm test:e2e:smoke`  | CI — login, entry, trends, insights                      |
| User journey regression | `pnpm test:e2e:journeys` | W1–W7 auth/onboarding/maturity matrix (`user-journeys.spec.ts`) |
| Mobile regression      | `pnpm test:e2e:mobile` | **18/18 passed** (serial, `--workers=1`)                 |

### Not required for production deploy

- Figma Code Connect publish (Sprint H)
- Full auth/onboarding Playwright state matrix
- Phase 5 wide-screen desktop layouts
- Password recovery UI (backend contract pending)

---

## Route & screen matrix

Legend: **Mobile** / **Web** = surface readiness (green / yellow / red).  
**Figma** = canonical sprint board. **E2E** = automated browser coverage.

| Screen            | Routes                                                               | Mobile | Web    | Figma sprint            | E2E                                                |
| ----------------- | -------------------------------------------------------------------- | ------ | ------ | ----------------------- | -------------------------------------------------- |
| Home / Today      | `/`                                                                  | Green  | Green  | S5 `121:2292`           | Dark theme smoke                                   |
| Entry             | `/entries/new`, `/entries/day/[date]`                                | Green  | Green  | S1 `48:1089`            | `mobile-entry-foundation`                          |
| Trends            | `/trends`                                                            | Green  | Green  | S2 `59:1285`            | `mobile-trends-foundation`                         |
| Insights          | `/insights`, `/insights/disclaimer`                                  | Green  | Green  | S3 `98:1573`            | `mobile-insights-foundation`, `m7-insights-mobile` |
| Settings          | `/settings`, `/settings/tags`, `/settings/symptoms`, `/settings/app` | Green  | Green  | S4 `105:1626`, Tags B1b | `mobile-supporting-flows`                          |
| Onboarding / Auth | `/onboarding/*`, `/auth/*`                                           | Green  | Yellow | S4 B4–B5, B4b           | Smoke + Figma; no full state matrix                |
| Offline / PWA     | `/offline`, `/settings/app`, banners                                 | Green  | Green  | S4 B3/B6                | Supporting flows + lifecycle tests                 |
| Status / Dev      | `/status`, `/dev`                                                    | —      | —      | —                       | Internal only                                      |

**Secondary routes (23 `+page.svelte` files):** all primary user journeys above are
implemented; `/insights/disclaimer` is static legal copy (Figma frame deferred).

---

## Shell & responsive model

| Breakpoint     | Shell                          | Entry                               | Trends                          | Insights                        |
| -------------- | ------------------------------ | ----------------------------------- | ------------------------------- | ------------------------------- |
| **390 × 844**  | Bottom `AppNav`, 44 px targets | Compact optional details            | Summary first, detail on demand | `MobileInsightLead` before tabs |
| **430 × 932**  | Same                           | Same                                | Detail canvas toggle            | Matrix tab hides lead           |
| **≥ 768 px**   | Side rail                      | Expanded workspace (Phase 5 polish) | Full compare panel              | Analysis-first, no mobile lead  |
| **1280 × 900** | Desktop sanity                 | No compact toggle                   | Full canvas visible             | Stage header + four-card feed   |

Theme: `data-theme` light/dark on `<html>`; persisted `correlcore-theme`. Dark smoke:
[`mobile-theme-parity.spec.ts`](../../apps/web/tests/e2e/mobile-theme-parity.spec.ts).

---

## Component system

**~60 Svelte components** under `apps/web/src/lib/components/` grouped by domain:

| Layer        | Examples                                                            | Status                                 |
| ------------ | ------------------------------------------------------------------- | -------------------------------------- |
| **Common**   | Button, Panel, ScreenHeader, AppNav, TabBar, ThemeToggle            | Shared; Figma + Code Connect templates |
| **Entries**  | EntryForm, ScaleSlider, TagPicker, SymptomChecker, EntrySheet       | Mobile capture signed off              |
| **Home**     | HomeDailyBrief, HomeSparkline, HomeTodayContext, MetricCard         | S5 three-zone contract                 |
| **Trends**   | MobileTrendsSummary, TrendsComparePanel, MetricTimeseries, heatmaps | Mobile summary / web-primary charts    |
| **Insights** | MobileInsightLead, InsightCard, InsightFeed, InsightMatrix          | Hierarchy aligned Sprint 3             |
| **Auth**     | PasswordStrength                                                    | Login/register in code + Figma B4b     |

**Classification (design intent):**

- **Shared:** work on both surfaces with density differences (Button, InsightCard, …)
- **Mobile-specialized:** capture UX (ScaleSlider, TagPicker, SymptomChecker)
- **Web-primary:** full analytical widgets (MetricTimeseries, ComparisonHeatmap, …) — hidden or summarized on mobile by design
- **Needs split / variant:** composition differs by surface (EntryForm, AppNav) — not a second codebase

Component matrix detail: [`mobile-web-audit.json`](../../apps/web/figma/mobile-web-audit.json) → `componentMatrix`.

---

## Design system & Figma

**File:** [CorrelCore Design System](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS)  
**Node ledger:** [`apps/web/figma/correlcore-figma-map.json`](../../apps/web/figma/correlcore-figma-map.json)

| Sprint | Scope                                                                 | Status         |
| ------ | --------------------------------------------------------------------- | -------------- |
| **E**  | Light/Dark tokens, Theme Reference, legacy deprecation, S3 layout     | ✅             |
| **F**  | Home S5, Auth entry, Tags, Matrix @430                                | ✅             |
| **G**  | 21 component sets, 20 Code Connect templates, variant docs `131:3864` | ✅             |
| **H**  | Live Code Connect publish                                             | ⏸ Seat + token |
| **I**  | QA matrix, dark E2E, audit refresh                                    | ✅             |

**Dark mode in Figma:** use **Dark mode previews** rows on Sprint boards 1–5 or
Theme Reference / Dark `120:2096` — not light frames with mode toggle alone (AppNav
instance inheritance limitation).

**Legacy (do not implement from):** `28:328`, `28:615`, `21:*` componentized screens.

---

## Quality & test inventory

### Vitest (unit / component / route)

- **97 test files**, **473 tests** (2026-06-27 local run)
- Route contracts: `surface-contract`, `screen-chrome`, `appNav`, page tests for home/trends/settings/tags
- Code Connect contract: `code-connect-contract.test.ts` (11 tests, 20 templates)

### Playwright (E2E)

| Suite             | Specs                                                | Purpose                                 |
| ----------------- | ---------------------------------------------------- | --------------------------------------- |
| Smoke (CI)        | `smoke.spec.ts`                                      | Login, entry autosave, trends, insights |
| Mobile foundation | 4 × `mobile-*-foundation`, `mobile-supporting-flows` | 390/430/1280 per flow                   |
| M7 mobile         | `m7-insights-mobile.spec.ts`                         | Touch, tabs, co-occurrence              |
| Theme parity      | `mobile-theme-parity.spec.ts`                        | Dark @390, five primary routes          |
| Surface           | `surface-foundation.spec.ts`                         | Shell primitives                        |

**Total mobile suite:** 18 tests via `npm run test:e2e:mobile` (run with `--workers=1`).  
**User journeys:** 12 tests via `pnpm test:e2e:journeys` — auth/onboarding/maturity matrix.

**GUI optimization:** [`GUI_OPTIMIZATION_IMPLEMENTATION_PLAN.md`](GUI_OPTIMIZATION_IMPLEMENTATION_PLAN.md) · Issues [#250](https://github.com/Sturmi77/correlcore/issues/250)–[#272](https://github.com/Sturmi77/correlcore/issues/272)

### CI pipeline (`ci-web.yml`)

`lint` → `format:check` → `typecheck` → `check:contrast` → `test` → `build` → `test:e2e:smoke`

Mobile E2E is **not** in default CI; run before release or add to scheduled workflow.

---

## Internationalization & accessibility

- **Locales:** `en`, `de` — completeness guarded by `localeCompleteness.test.ts`
- **No-gamification copy:** `noGamificationCopy.test.ts` (ADR principles)
- **Touch targets:** ≥ 44 px on mobile controls (`app.css`, component tests, E2E)
- **Contrast:** ADR-0027 pairs enforced in CI via `pnpm check:contrast`
- **Screen readers:** `aria-*` on AppNav, ScaleSlider, SymptomChecker, insight stage meter

---

## Known deferrals & open tracks

### Not blocking production deploy

| Item                                                    | Owner / track                                      |
| ------------------------------------------------------- | -------------------------------------------------- |
| Code Connect publish (Sprint H)                         | Figma admin — Dev/Full seat + `FIGMA_ACCESS_TOKEN` |
| Figma Dev Mode live snippets                            | Same as H                                          |
| Insights disclaimer Figma frame                         | Static route; low churn                            |
| Full auth/onboarding E2E matrix                         | Optional hardening                                 |
| Dedicated Playwright for every verify-email permutation | Manual + Figma B4                                  |

### Product / backend (out of frontend scope)

| Item                          | Notes                             |
| ----------------------------- | --------------------------------- |
| Password recovery             | No backend contract → no UI       |
| Reminders, account deletion   | Placeholder / backlog             |
| Dexie background sync queue   | ADR-0009 — Entry-owned retry only |
| Health Connect import consent | M7 backlog                        |

### Phase 5 — desktop consolidation (next frontend track)

- Entry **web** workspace layout (currently yellow)
- Auth/onboarding **web** density polish (yellow)
- Wide Home dashboard (beyond S5 mobile three-zone)
- Split views, sticky analytics chrome @1280+

Plan pointer: [`MOBILE_WEB_IMPLEMENTATION_PLAN.md`](MOBILE_WEB_IMPLEMENTATION_PLAN.md).

---

## Production-grade acceptance (design system)

From [`FIGMA_PRODUCTION_GRADE_SPRINT_PLAN.md`](../FIGMA_PRODUCTION_GRADE_SPRINT_PLAN.md):

| #   | Criterion                                | Status      |
| --- | ---------------------------------------- | ----------- |
| 1   | Theme (Figma + contrast)                 | ✅          |
| 2   | Screen coverage S1–S5                    | ✅          |
| 3   | Components = map = templates             | ✅ (local)  |
| 4   | Code Connect live OR deferral documented | ✅ Deferred |
| 5   | Legacy hygiene                           | ✅          |
| 6   | QA evidence                              | ✅          |

---

## Document index

| Document                                                                            | Purpose                          |
| ----------------------------------------------------------------------------------- | -------------------------------- |
| **This file**                                                                       | Current frontend status snapshot |
| [`FRONTEND.md`](../FRONTEND.md)                                                     | Principles, ADR links, UX rules  |
| [`MOBILE_WEB_AUDIT.md`](MOBILE_WEB_AUDIT.md)                                        | Screen/component audit narrative |
| [`MOBILE_WEB_IMPLEMENTATION_PLAN.md`](MOBILE_WEB_IMPLEMENTATION_PLAN.md)            | Phase ledger & next sprints      |
| [`MOBILE_WEB_CLOSEOUT_QA.md`](../quality/MOBILE_WEB_CLOSEOUT_QA.md)                 | Phases 0–4 sign-off              |
| [`FIGMA_PRODUCTION_GRADE_QA.md`](../quality/FIGMA_PRODUCTION_GRADE_QA.md)           | Design system sign-off           |
| [`FIGMA_PRODUCTION_GRADE_SPRINT_PLAN.md`](../FIGMA_PRODUCTION_GRADE_SPRINT_PLAN.md) | Sprints E–I plan                 |
| [`apps/web/figma/README.md`](../../apps/web/figma/README.md)                        | Figma nodes, templates, publish  |
| [`UI_COMPONENT_SYSTEM.md`](UI_COMPONENT_SYSTEM.md)                                  | Component conventions            |

---

## Audit evidence log (2026-06-27)

Commands run for this snapshot:

```bash
cd apps/web && npm run test                    # 97 files, 473 passed
cd apps/web && npm run test:e2e:mobile -- --workers=1   # 18 passed
npx @figma/code-connect@latest connect publish --dry-run  # 20 templates parsed
```

MCP `get_code_connect_map` for Button `6:64`: blocked (Dev/Full seat) — documented deferral.

**Recommendation:** Safe to **deploy the application**. Schedule Sprint H when Figma
seat is available; schedule Phase 5 when desktop density is a product priority.
