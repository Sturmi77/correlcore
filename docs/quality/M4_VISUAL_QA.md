# M4 Visual QA — Quick Wins + PWA Closeout

Date: 2026-06-30  
Sprint: **M4-C** (milestone closeout)  
Companion: [`M4_SPRINT_STATUS.md`](../M4_SPRINT_STATUS.md) · [`CLOSEOUT_SPRINT_PLAN.md`](../CLOSEOUT_SPRINT_PLAN.md)

## Scope

M4 quick-win surfaces shipped on `main` (PR #211):

- Entry form / sheet: Morning / Noon / Evening slot chips behind `+ More`
- Cycle-day field behind `+ More` (neutral 1–35, no phase inference)
- Guided `/onboarding` (3 steps, tag suggestions, skip path)
- Trends Mood: `Raw | Smoothed` toggle for 30D+ ranges
- Trends Health: neutral cycle-day strip when data exists
- Settings > Developer: phase switcher, onboarding preview iframe, entry-count mock
- Home PWA install banner (`beforeinstallprompt`, dismiss persisted)
- `/offline` fallback route and service-worker app-shell cache

Deferred to **M4.1 — Offline-First Sync**: Dexie delta sync (#10), conflict log (#24).

## Verification method

| Layer            | Evidence                                              | Date       |
| ---------------- | ----------------------------------------------------- | ---------- |
| Web unit         | Vitest (slots, SMA smoothing, PWA stores, settings)   | 2026-06-30 |
| E2E smoke        | `pnpm --filter @correlcore/web test:e2e:smoke`        | 2026-06-30 |
| Mobile E2E       | `mobile-entry-foundation`, `mobile-supporting-flows`  | 2026-06-30 |
| Rendered browser | Manual smoke on local dev server post M4-C gates      | 2026-06-30 |

## Viewport matrix

| Surface                         | 375  | 768  | 1280 | Light | Dark |
| ------------------------------- | ---- | ---- | ---- | ----- | ---- |
| Entry form slot chips           | Pass | Pass | Pass | Pass  | Pass |
| Guided onboarding flow          | Pass | Pass | Pass | Pass  | Pass |
| Trends Mood smoothing toggle    | Pass | Pass | Pass | Pass  | Pass |
| Trends Health cycle-day strip   | Pass | Pass | Pass | Pass  | Pass |
| Settings Developer controls     | Pass | Pass | Pass | Pass  | Pass |
| Home PWA install banner         | Pass | Pass | Pass | Pass  | Pass |
| `/offline` fallback page        | Pass | Pass | Pass | Pass  | Pass |

## Core interactions

| Interaction                                      | Status |
| ------------------------------------------------ | ------ |
| Slot chip updates entry slot / delta lookup      | Pass   |
| Smoothing toggle persists in `cc_trend_smooth`     | Pass   |
| Onboarding creates custom tags by slug           | Pass   |
| Dev Mode phase override affects insight maturity | Pass   |
| Install banner dismiss persists                  | Pass   |
| Offline event shows PWA offline banner           | Pass   |
| SW caches shell; API routes not cached           | Pass   |

## Static gates (M4-C)

| Gate                                | Result       |
| ----------------------------------- | ------------ |
| GitHub CI on PR branch (#243)       | Pass (2026-06-30) |
| Local `.\scripts\local-quality.ps1` | Rerun on contributor machine before merge |

## Manual device notes

`beforeinstallprompt` and iOS Add-to-Home-Screen behaviour remain browser-controlled.
Automated closeout covers install-banner UX; native install-prompt spot-check on Android Chrome
and iOS Safari is tracked for beta/release prep (M9).

## Result

**M4 quick wins + PWA visual QA: passed.** Milestone M4 closeout criterion met. Offline sync follow-ups tracked under M4.1.
