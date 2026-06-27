# Figma Production-Grade QA (Sprint I)

Date: 2026-06-27  
Scope: Design-system parity after Sprints E–G; Sprint H (Code Connect publish) **deferred** until Figma Dev/Full seat.  
Plan: [`docs/FIGMA_PRODUCTION_GRADE_SPRINT_PLAN.md`](../FIGMA_PRODUCTION_GRADE_SPRINT_PLAN.md)

**Result: Production-grade design system signed off for E + F + G + I (partial H).**

Prior mobile closeout QA: [`MOBILE_WEB_CLOSEOUT_QA.md`](MOBILE_WEB_CLOSEOUT_QA.md).

---

## Sprint status ledger

| Sprint | Title                  | Status | Notes                                                 |
| ------ | ---------------------- | ------ | ----------------------------------------------------- |
| E      | Tokens & hygiene       | ✅     | Light/Dark modes, Theme Reference, legacy deprecation |
| F      | Missing screen flows   | ✅     | Home S5, Auth entry, Tags, Matrix @430                |
| G      | Components + templates | ✅     | 20 Code Connect templates, 21 component sets          |
| H      | Code Connect publish   | ⏸      | **Blocked:** Org/Enterprise Dev or Full seat required |
| I      | Production QA          | ✅     | This document                                         |

**Sprint H owner:** Design / Figma org admin — assign Dev or Full seat, publish library, run `figma connect publish`.

---

## Evidence summary

| Layer              | Method                         | Result (2026-06-27)                                                       |
| ------------------ | ------------------------------ | ------------------------------------------------------------------------- |
| Mobile E2E (light) | `npm run test:e2e:mobile`      | **18/18 pass** (serial, 2026-06-27)                                       |
| Dark theme E2E     | `mobile-theme-parity.spec.ts`  | **1/1 pass** @390 — `data-theme=dark`, nav visible, no H-scroll           |
| Contrast gate      | `pnpm check:contrast`          | ADR-0027 pairs in `app.css`; **CI gate** in `ci-web.yml`                  |
| Figma screens      | Sprint 1–5 + dark preview rows | 45+ dark clones + Theme Reference `120:2096`                              |
| Code Connect       | Local templates                | 20 files parsed; **publish pending** `FIGMA_ACCESS_TOKEN` + Dev/Full seat |

**Contrast note:** `check:contrast` also scans built CSS under `apps/web/build` for legacy token names. Run on a clean tree or rely on CI if local build artifacts are stale.

---

## Viewport matrix

Mandatory: **390 × 844**, **430 × 932**. Sanity: **1280 × 900**.

| Flow            | Figma sprint  | 390 L | 430 L | 1280 | H-scroll | Touch ≥44 px | E2E / evidence                                     |
| --------------- | ------------- | ----- | ----- | ---- | -------- | ------------ | -------------------------------------------------- |
| Home / Today    | S5 `121:2292` | ✓     | ✓     | ✓    | ✓        | ✓            | Dark theme spec; Figma dark row `127:2586`         |
| Entry           | S1 `48:1089`  | ✓     | ✓     | ✓    | ✓        | ✓            | `mobile-entry-foundation`                          |
| Trends          | S2 `59:1285`  | ✓     | ✓     | ✓    | ✓        | ✓            | `mobile-trends-foundation`                         |
| Insights        | S3 `98:1573`  | ✓     | ✓     | ✓    | ✓        | ✓            | `mobile-insights-foundation`, `m7-insights-mobile` |
| Settings / Tags | S4 `105:1626` | ✓     | ✓     | ✓    | ✓        | ✓            | `mobile-supporting-flows`; Tags B1b                |
| Auth entry      | S4 B4b        | ✓†    | ✓†    | —    | ✓†       | ✓†           | Figma frames; route code                           |
| Onboarding      | S4 B5         | ✓†    | ✓†    | —    | ✓†       | ✓†           | Figma + manual                                     |
| Offline / PWA   | S4 B3/B6      | ✓     | ✓     | ✓    | ✓        | ✓            | Supporting flows E2E                               |

† Auth/onboarding: no full state-matrix Playwright file; Figma parity complete.

---

## Theme matrix (Light + Dark)

### Browser (rendered)

| Check                                                        | Light                     | Dark                               |
| ------------------------------------------------------------ | ------------------------- | ---------------------------------- |
| Primary routes @390 (`/`, Entry, Trends, Insights, Settings) | E2E suite (default theme) | `mobile-theme-parity.spec.ts`      |
| `data-theme` on `<html>`                                     | Default                   | Injected + `correlcore-theme=dark` |
| App shell nav visible                                        | ✓                         | ✓                                  |
| Horizontal overflow                                          | ✓                         | ✓                                  |
| Token contrast (ADR-0027)                                    | `app.css` + CI            | Same pairs for `:root` / dark      |

### Figma

| Check                                            | Light                      | Dark                                      |
| ------------------------------------------------ | -------------------------- | ----------------------------------------- |
| Foundation components (Button, Panel, AppNav, …) | `CorrelCore / Color` Light | Variable Dark mode on sets                |
| Sprint boards                                    | Light state rows           | **Dark mode previews** rows (S1–S5)       |
| Cross-sprint reference                           | —                          | Theme Reference / Dark `120:2096`         |
| Instance dark inheritance                        | N/A                        | Explicit Dark mode on clones (AppNav fix) |

**Do not judge dark parity** by toggling mode on light sprint frames alone — nested instances (e.g. AppNav) may stay on Light values. Use dark preview rows or Theme Reference board.

---

## Figma ↔ code coverage

| Area                                       | Figma                          | Code Connect template  | Live publish |
| ------------------------------------------ | ------------------------------ | ---------------------- | ------------ |
| Foundation (Button, Panel, …)              | ✅                             | ✅                     | ⏸ Sprint H   |
| Insights (Card, StageHeader, Matrix, Lead) | ✅                             | ✅                     | ⏸            |
| Entry (ScaleSlider, TagChip, FormField)    | ✅                             | ✅                     | ⏸            |
| Trends (MobileTrendsSummary)               | ✅ `131:31`                    | ✅                     | ⏸            |
| SymptomChecker                             | ✅ `131:3914` + doc `131:3864` | — (screen composition) | —            |
| Home S5                                    | ✅ `121:2292`                  | —                      | —            |

Map: [`apps/web/figma/correlcore-figma-map.json`](../../apps/web/figma/correlcore-figma-map.json)

---

## Static gates (run before release)

```bash
cd apps/web && npm run test:e2e:mobile
cd apps/web && npx playwright test tests/e2e/mobile-theme-parity.spec.ts --workers=1
pnpm check:contrast   # prefer clean tree or CI
```

---

## Known deferrals (not blocking production-grade sign-off)

| Item                                   | Track                          |
| -------------------------------------- | ------------------------------ |
| Code Connect live publish              | Sprint H — Figma Dev/Full seat |
| Password recovery UI                   | Backend contract               |
| Phase 5 desktop density                | Separate track                 |
| Full auth/onboarding Playwright matrix | Optional hardening             |
| Insights disclaimer frame              | F4 deferred (static copy)      |

---

## Sign-off

| Dimension                           | Verdict                 |
| ----------------------------------- | ----------------------- |
| Theme (Figma + browser dark smoke)  | **Pass**                |
| Screen coverage S1–S5               | **Pass**                |
| Component library + local templates | **Pass** (Sprint G)     |
| Code Connect live                   | **Deferred** (Sprint H) |
| Hygiene (legacy deprecated)         | **Pass** (Sprint E)     |
| Evidence (this doc + audits)        | **Pass**                |

**Production-grade design system:** ✅ for implementation handoff. Complete **Sprint H** when Figma seat is available to activate live Dev Mode snippets.

---

## Quick links

| Artifact                                  | Location                                                                               |
| ----------------------------------------- | -------------------------------------------------------------------------------------- |
| Theme Reference / Dark                    | [Figma 120:2096](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=120-2096) |
| Variant docs (TagPicker / SymptomChecker) | [Figma 131:3864](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=131-3864) |
| Audit overview                            | [Figma 31:1089](https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=31-1089)   |
| Mobile audit                              | [`docs/frontend/MOBILE_WEB_AUDIT.md`](../frontend/MOBILE_WEB_AUDIT.md)                 |
