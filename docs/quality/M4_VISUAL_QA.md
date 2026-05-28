# M4 Visual QA

Last updated: 2026-05-28

## Scope

Visual QA covers the M4 quick-win surfaces:

- Entry form and entry sheet slot chips
- Cycle-day field behind `+ More`
- Guided `/onboarding` flow
- Trends Mood smoothing toggle
- Trends Health cycle-day context
- Settings Developer phase controls and onboarding preview
- Home PWA install banner
- `/offline` fallback page

## Breakpoints

| Width   | Theme | Status                      | Notes                                                                        |
| ------- | ----- | --------------------------- | ---------------------------------------------------------------------------- |
| 375 px  | Light | Pending rendered browser QA | Verify no horizontal overflow in onboarding, entry form, and settings modal. |
| 375 px  | Dark  | Pending rendered browser QA | Verify install banner action wrapping and cycle strip scrolling.             |
| 768 px  | Light | Pending rendered browser QA | Verify side-nav layout and modal sizing.                                     |
| 768 px  | Dark  | Pending rendered browser QA | Verify charts and smoothing controls.                                        |
| 1280 px | Light | Pending rendered browser QA | Verify no oversized panel typography.                                        |
| 1280 px | Dark  | Pending rendered browser QA | Verify PWA/offline surfaces and developer controls.                          |

## Local Static Checks

- Web typecheck: passed locally on 2026-05-28 after the main M4 code changes.
- Final Web typecheck/test rerun: blocked in the current sandbox by access to
  `.svelte-kit` / `vite.config.ts`.
- Backend Ruff/Pytest rerun: blocked in the current sandbox by `uv` cache access.
- Browser-rendered screenshots: pending after local dev server verification.

## Manual Mobile Notes

Android Chrome and iOS Safari install behavior require manual device/browser
checks because `beforeinstallprompt` availability is browser-controlled.
